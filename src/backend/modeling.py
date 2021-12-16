import asyncio
import os, time, sys, io
import pandas
import requests, aiohttp
from dotenv import load_dotenv, main

import rasterio as rio
from rasterio import features
import geopandas as gp
from geopandas.geodataframe import GeoDataFrame
import numpy as np
import shapely.speedups

import logging
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, track
from rich import box

if __name__ == "__main__":
    log_level = "CRITICAL"
    # Rich console
    console = Console()
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        # handlers=[RichHandler(rich_tracebacks=True)],
    )

log = logging.getLogger("rich")

load_dotenv()


def strToBool(str):
    """converts "True", "False" string to bool"""
    if str == "True" or str == "true":
        return True
    elif str == "False" or str == "false":
        return False
    else:
        return None


# constants
DEBUG = strToBool(os.environ.get("DEBUG"))
ASYNC_DL = strToBool(os.environ.get("ASYNC_DL"))

# Implement Null coalescing operator if it becomes available anytime
if DEBUG is None:
    DEBUG = False
if ASYNC_DL is None:
    ASYNC_DL = True

input_folder = "./input/"
tile_folder = input_folder + "tiles/"
output_folder = "./output/"

tile_buffer = []
# create folders
if not os.path.exists(tile_folder):
    os.makedirs(tile_folder)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# tile_url = f"https://www.wcs.nrw.de/geobasis/wcs_nw_dgm?REQUEST=GetCoverage&SERVICE=WCS&VERSION=2.0.1&COVERAGEID=nw_dgm&FORMAT=image/tiff&SUBSET=x({x1},{x2})&SUBSET=y({y1},{y2})&OUTFILE=dgm&APP=timonline"
tile_url = "https://www.wcs.nrw.de/geobasis/wcs_nw_dgm?REQUEST=GetCoverage&SERVICE=WCS&VERSION=2.0.1&COVERAGEID=nw_dgm&FORMAT=image/tiff&"
filename_tile = tile_folder + "tile"
river_shapefile = input_folder + "waterwaySHP/gsk3c_gew_kanal_plm.shp"

# https://betterprogramming.pub/how-to-make-parallel-async-http-requests-in-python-d0bd74780b8a


async def async_download(urls):
    list = []
    step = 0
    with Progress() as progress:
        if __name__ == "__main__":
            task = progress.add_task("Downloading", total=len(urls))

        async def fetch_async(entry, session):
            url, path = entry

            async with session.get(url) as response:
                if response.status == 200:
                    inmemoryfile = io.BytesIO(await response.content.read())
                    if __name__ == "__main__":
                        progress.update(task_id=task, advance=1)
                    return list.append(inmemoryfile)
                else:
                    console.print(response.status_code, response.url)
                    return

        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[fetch_async(url, session) for url in urls])
            return list


def setLocation(x, y, r):
    """
    get rect raster box of input utm coords
    """
    x = int(x)
    y = int(y)
    r = int(r)
    location = [x - r, x + r, y - r, y + r]
    return location


def convertToUTM32(x, y):
    df = pandas.DataFrame({"lat": [x], "lon": [y]})
    gdf = GeoDataFrame(df, geometry=gp.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    gdf = gdf.to_crs(epsg="25832")
    x = gdf.geometry.x[0]
    y = gdf.geometry.y[0]
    return [x, y]


def createRasterList(tile_buffer):
    arr_list = []
    for tile in tile_buffer:
        with rio.open(tile, "r") as k1:
            arr = k1.read(1)
            arr_list.append(
                dict(
                    {
                        "arr": arr,
                        "bbox": k1.bounds,
                        "trafo": k1.transform,
                        "shape": k1.shape,
                        "crs": k1.crs,
                    }
                )
            )
    print(sys.getsizeof(arr_list))
    return arr_list


def emptyFolder(folder):
    for f in os.listdir(folder):
        if not f.endswith(".tiff"):
            continue
        os.remove(os.path.join(folder, f))


def downloadTiff(entry):
    """
    download Tiff from url and save in file of current directory
    """
    url, filename_tiff = entry
    with requests.get(url) as r:
        if r.status_code == 200:
            inmemoryfile = io.BytesIO(r.content)
            return inmemoryfile
        else:
            log.warn(r.status_code, r.url)
            return None


def calcMeanRiverHeight(riverSHPfilename, raster_list):
    """
    calculate mean elevation of river line on DGM
    """
    mean_river_height_list = []
    for tile in raster_list:
        arr = tile["arr"]
        bbox = tile["bbox"]
        transform = tile["trafo"]

        river_gdf = gp.read_file(riverSHPfilename, bbox=bbox)
        shapes = ((geom, 255) for geom in river_gdf.geometry)
        try:
            burned = features.rasterize(
                shapes=shapes, out_shape=tile["shape"], transform=transform
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
    res_json = result.to_json()
    result.to_file(output_folder + "cleanflood.geojson", driver="GeoJSON")
    log.debug(
        "[bold black on green]output file: " + output_folder + "cleanflood.geojson"
    )
    return res_json


def createFloodzoneMultiTile(floodheight: float, location: list):
    """
    create Floodzone geoJSON from location with flood height
    """
    tile_buffer = []
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
            tile_url
            + f"SUBSET=x({bbox[0]},{bbox[1]})&SUBSET=y({bbox[2]},{bbox[3]})&OUTFILE=tile{str(i)}"
        )
        urls.append([url, filename_tile + str(i) + ".tiff"])
    emptyFolder(tile_folder)

    if ASYNC_DL:
        tile_buffer.extend(asyncio.run(async_download(urls)))
    else:
        for url in urls:
            tile_buffer.append(downloadTiff(url))

    raster_list = createRasterList(tile_buffer)
    downloadtime = time.time()
    # calculate mean river height of all tiles
    if __name__ == "__main__":
        with console.status("[bold green]calc mean river height"):
            mean_river_height = calcMeanRiverHeight(river_shapefile, raster_list)
    else:
        mean_river_height = calcMeanRiverHeight(river_shapefile, raster_list)

    # mean_river_height = 60
    if mean_river_height == None:
        return log.info("No rivers in selected location!")
    else:
        log.info(
            f"mean height of rivers:{round(mean_river_height,2)} | flood level:{round(mean_river_height,2) + floodheight} m"
        )
        shapes = []
        # with console.status("[bold green]creating shapefile") as status:
        for tile in raster_list:
            arr = tile["arr"]
            bbox = tile["bbox"]
            transform = tile["trafo"]
            crs = tile["crs"]
            # if cell value under level height -> set 0
            arr[arr < mean_river_height + floodheight] = 0
            # else set cell value -> 1
            arr[arr != 0] = 1
            mod_raster = arr

            # get shapes from raster    https://gist.github.com/sgillies/8655640
            shapes.extend(
                list(
                    features.shapes(
                        mod_raster,
                        mask=(mod_raster != 1),
                        transform=transform,
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
    if __name__ == "__main__":
        with console.status("[bold green]cleanup floodshape"):
            flood_json = cleanupFloodzoneShape(flood_gdf, river_gdf)
    else:
        flood_json = cleanupFloodzoneShape(flood_gdf, river_gdf)
        return flood_json

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
    if DEBUG:
        # Bochum Dahlhausen
        location = (370500, 5698700, 4000)
        flood_height = 1
        console.print("[bold red]~~~ Flood model cli ~~~")
        console.print(f"Async Download: {ASYNC_DL} | Debug: {DEBUG} ")
    else:
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
    console.print("[green]DONE !")
