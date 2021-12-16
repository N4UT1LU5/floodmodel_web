import asyncio
import os, time
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
from rich.progress import track
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
async def fetch_async(entry, session):
    url, path = entry
    try:
        async with session.get(url) as response:
            if response.status == 200:
                # print("dl:" + path)
                with open(path, "wb") as f:
                    f.write(await response.read())
                # response.clear()
                # pass
            else:
                console.print(response.status_code, response.url)
                return
    except Exception as e:
        print(e)


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def async_download(urls):
    conc_req = 5
    conn = aiohttp.TCPConnector(limit=conc_req, ttl_dns_cache=300)
    # session = aiohttp.ClientSession(connector=conn)

    # await gather_with_concurrency(conc_req, *[fetch_async(i, session) for i in urls])
    # for i in urls:
    #     await fetch_async(i, session)
    # await session.close()
    async with aiohttp.ClientSession(connector=conn) as session:
        await asyncio.gather(*[fetch_async(url, session) for url in urls])


def setLocation(x, y, r):
    """
    get rect raster box of input utm coords
    """
    x = int(x)
    y = int(y)
    r = int(r)
    location = [x - r, x + r, y - r, y + r]
    return location


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

    def dl():
        if ASYNC_DL:
            asyncio.run(async_download(urls))
        else:
            for url in urls:
                downloadTiff(url)

    if __name__ == "__main__":
        with console.status(f"[bold green]Downloading {len(bbox_list)} tile(s)") as s:
            dl()
    else:
        dl()

    downloadtime = time.time()
    # calculate mean river height of all tiles
    mean_river_height = calcMeanRiverHeight(river_shapefile, tile_folder)

    if mean_river_height == None:
        return log.info("No rivers in selected location!")

    else:
        log.info(
            f"mean height of rivers:{round(mean_river_height,2)} | flood level:{round(mean_river_height,2) + floodheight} m"
        )
        shapes = []
        # with console.status("[bold green]creating shapefile") as status:
        for tile_file in os.listdir(tile_folder):
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
        location = (370500, 5698700, 2000)
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
