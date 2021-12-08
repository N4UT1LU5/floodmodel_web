import asyncio
import os, time
import requests, aiohttp

import rasterio as rio
from rasterio import features
import geopandas as gp
from geopandas.geodataframe import GeoDataFrame
import numpy as np
import shapely.speedups

from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import box

# Rich console
console = Console()

# constants
input_folder = "./input/"
tile_folder = input_folder + "tiles/"
output_folder = "./output/"
# create folders
if not os.path.exists(tile_folder):
    os.makedirs(tile_folder)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# kachel_url = f"https://www.wcs.nrw.de/geobasis/wcs_nw_dgm?REQUEST=GetCoverage&SERVICE=WCS&VERSION=2.0.1&COVERAGEID=nw_dgm&FORMAT=image/tiff&SUBSET=x({x1},{x2})&SUBSET=y({y1},{y2})&OUTFILE=dgm&APP=timonline"
kachel_url = "https://www.wcs.nrw.de/geobasis/wcs_nw_dgm?REQUEST=GetCoverage&SERVICE=WCS&VERSION=2.0.1&COVERAGEID=nw_dgm&FORMAT=image/tiff&"
filename_kachel = tile_folder + "tile"
river_shapefile = input_folder + "waterwaySHP/gsk3c_gew_kanal_plm.shp"

# https://betterprogramming.pub/how-to-make-parallel-async-http-requests-in-python-d0bd74780b8a
async def fetch_async(entry, session):
    url, path = entry
    async with session.get(url) as response:
        if response.status == 200:
            with open(path, "wb") as f:
                f.write(await response.read())
        else:
            console.print(response.status_code, response.url)
            return None


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def async_download(urls):

    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    session = aiohttp.ClientSession(connector=conn)
    conc_req = 10

    await gather_with_concurrency(conc_req, *[fetch_async(i, session) for i in urls])
    await session.close()


def setLocation(x, y, r):
    """
    get rect raster box of input utm coords
    """
    location = [x - r, x + r, y - r, y + r]
    return location


def emptyFolder(folder):
    for f in os.listdir(folder):
        if not f.endswith(".tiff"):
            continue
        os.remove(os.path.join(folder, f))


def downloadTiff(url, filename_tiff):
    """
    download Tiff from url and save in file of current directory
    """
    with requests.get(url) as r:
        if r.status_code == 200:
            with open(filename_tiff, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return filename_tiff
        else:
            console.print(r.status_code, r.url)
            return None


def calcMeanRiverHeight(riverSHPfilename, tilefolder):
    """
    calculate mean elevation of river line on DGM
    """
    mean_river_height_list = []
    for f in os.listdir(tilefolder):
        if f.endswith(".tiff"):
            with rio.open(tilefolder + f, "r") as k1:
                arr = k1.read(1)
                bbox = k1.bounds
                transform = k1.transform
            river_gdf = gp.read_file(riverSHPfilename, bbox=bbox)
            shapes = ((geom, 255) for geom in river_gdf.geometry)
            try:
                burned = features.rasterize(
                    shapes=shapes, out_shape=k1.shape, transform=transform
                )
            except ValueError:
                continue
            # create mask array
            burned[burned == 0] = 1
            burned[burned == 255] = 0
            burned_int = burned.astype(int)

            masked_array = np.ma.array(arr, mask=burned_int)
            mean_river_height = np.mean(masked_array)
            if mean_river_height != None:
                mean_river_height_list.append(mean_river_height)

    return sum(mean_river_height_list) / len(mean_river_height_list)


def cleanupFloodzoneShape(floodzone_gdf: GeoDataFrame, river_gdf: GeoDataFrame):
    """
    remove polygons not connected to river and simplify geometry
    """
    # connect all touching polygons and than explode multipolygon into single polygons
    floodzone_gdf = floodzone_gdf.dissolve().explode(index_parts=True)
    # dissolve all rivers to one linestring
    river_gdf = river_gdf.dissolve()

    # create mask from all floodpolygons intersecting river linestring
    mask = floodzone_gdf.intersects(river_gdf.loc[0, "geometry"])

    # filter floodzones with mask
    result = floodzone_gdf.loc[mask]
    # dissolve floodzone and fill holes with buffer and simplify shape
    result = result.dissolve()
    result = result.buffer(3, 4).buffer(-3, 4).simplify(1)
    result.to_file(output_folder + "cleanflood.geojson", driver="GeoJSON")
    console.print(
        "[bold black on green]output file: " + output_folder + "cleanflood.geojson"
    )


def createFloodzoneMultiTile(floodheight: float, location: list):
    """
    docstring
    """
    shapely.speedups.enable()
    starttime = time.time()
    tile_raster_size = 1000

    x = location[0]
    y = location[1]
    r = location[2]

    outer_bbox = setLocation(x, y, r)
    bbox_list = [outer_bbox]
    x_cursor = outer_bbox[0]
    y_cursor = outer_bbox[2]

    if location[2] > 1000:
        bbox_list = []
        while y_cursor < outer_bbox[3]:
            while x_cursor < outer_bbox[1]:
                bbox_list.append(
                    [
                        x_cursor,
                        x_cursor + tile_raster_size,
                        y_cursor,
                        y_cursor + tile_raster_size,
                    ]
                )
                x_cursor += tile_raster_size
            y_cursor += tile_raster_size
            x_cursor = outer_bbox[0]

    # download all tiles
    urls = []
    for i in range(len(bbox_list)):
        bbox = bbox_list[i]
        url = (
            kachel_url
            + f"SUBSET=x({bbox[0]},{bbox[1]})&SUBSET=y({bbox[2]},{bbox[3]})&OUTFILE=tile{str(i)}"
        )
        urls.append([url, filename_kachel + str(i) + ".tiff"])

    with console.status(f"[bold green]Downloading {len(bbox_list)} tile(s)") as s:
        asyncio.run(async_download(urls))

    downloadtime = time.time()
    # calculate mean river height of all tiles
    mean_river_height = calcMeanRiverHeight(river_shapefile, tile_folder)

    if mean_river_height == None:
        return console.print("No rivers in selected location!")

    else:
        console.print(
            f"mean height of rivers:[bold blue]{round(mean_river_height,2)} m[/bold blue] \n flood level: [bold blue]{round(mean_river_height,2) + floodheight} m[/bold blue]"
        )
        shapes = []
        # with console.status("[bold green]creating shapefile") as status:
        for tile_file in track(os.listdir(tile_folder), "Creating shapes:"):
            if tile_file.endswith(".tiff"):
                with rio.open(tile_folder + tile_file, "r") as k1:
                    # read raster as array
                    arr = k1.read(1)
                    # if cell value under level height -> set 0
                    arr[arr < mean_river_height + floodheight] = 0
                    # else set cell value -> 1
                    arr[arr != 0] = 1
                    mod_raster = arr
                    crs = k1.crs
                    # get shapes from raster    https://gist.github.com/sgillies/8655640
                    shapes.extend(
                        list(
                            features.shapes(
                                mod_raster,
                                mask=(mod_raster != 1),
                                transform=k1.transform,
                            )
                        )
                    )

            # convert json dict into geodataframe
            shapejson = (
                {"type": "Feature", "properties": {}, "geometry": s}
                for i, (s, v) in enumerate(shapes)
            )
            collection = {"type": "FeatureCollection", "features": list(shapejson)}
            flood_gdf = gp.GeoDataFrame.from_features(collection["features"], crs=crs)

    river_gdf = gp.read_file(river_shapefile, bbox=flood_gdf.envelope)
    # convertRasterToShape(shape, "floodshape")
    emptyFolder(tile_folder)
    with console.status("[bold green]cleanup floodshape"):
        cleanupFloodzoneShape(flood_gdf, river_gdf)

    endtime = time.time()
    # timingtable
    dl_time = downloadtime - starttime
    comp_time = endtime - downloadtime
    total_time = endtime - starttime
    table = Table(show_header=True, header_style="bold yellow")
    table.add_column("download")
    table.add_column("processing")
    table.add_column("total")
    table.add_row(
        str(round(dl_time, 3)), str(round(comp_time, 3)), str(round(total_time, 3))
    )
    table.box = box.SIMPLE
    console.print("[bold] Runntimes in sec:")
    console.print(table)


def rndPre(nmbr, digits_before_decimal):
    return int(
        round(nmbr / (10 ** digits_before_decimal)) * (10 ** digits_before_decimal)
    )


if __name__ == "__main__":
    # Bochum Dahlhausen
    # location = (370500, 5698700, 2000)
    # flood_height = 1

    console.print("[bold blue]~~~ Flood model cli ~~~")
    flood_height = int(input("Enter floodwater height: ") or 1)
    x = int(input("Enter x: ") or 370500)
    y = int(input("Enter y: ") or 5698700)
    r = float(input("Enter radius [km]: ") or 1)
    r *= 1000
    x = rndPre(x, 3)
    y = rndPre(y, 3)
    r = rndPre(r, 2)

    table = Table(show_header=True, header_style="bold green")
    table.box = box.SIMPLE
    table.add_column("x")
    table.add_column("y")
    table.add_column("radius m")
    table.add_column("height m")
    location = [x, y, r]
    table.add_row(str(x), str(y), str(r), str(flood_height))
    console.print(table)

    createFloodzoneMultiTile(flood_height, location)
    console.print("[green]DONE ! ")
