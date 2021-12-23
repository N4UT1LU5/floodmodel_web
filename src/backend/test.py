import asyncio
from geopandas.geodataframe import GeoDataFrame
from rich.console import Console
from rich.progress import Progress
import modeling as mdl
import shapely.speedups
import os, time, sys
import requests, aiohttp
import rasterio as rio
import io
from owslib.wfs import WebFeatureService
import geopandas as gpd
import pandas as pd

alkis_simplified_wfs_url = "https://www.wfs.nrw.de/geobasis/wfs_nw_alkis_vereinfacht?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ave:GebaeudeBauwerk&OUTPUTFORMAT=text/xml;subtype=gml/3.2.1&"
tile_url = "http://www.wcs.nrw.de/geobasis/wcs_nw_dgm?REQUEST=GetCoverage&SERVICE=WCS&VERSION=2.0.1&COVERAGEID=nw_dgm&FORMAT=image/tiff&"


def downloadTiff(entry):
    """
    download Tiff from url and save in file of current directory
    """
    url, filename_tiff = entry
    # with rio.open(url) as dataset:
    #     print(dataset.profile)
    with requests.get(url) as r:
        if r.status_code == 200:
            inmemoryfile = io.BytesIO(r.content)
            return inmemoryfile


async def async_download(urls):
    list = []
    with Progress() as progress:
        if __name__ == "__main__":
            task = progress.add_task("Downloading", total=len(urls))

        async def fetch_async(entry, session):
            url = entry

            async with session.get(url) as response:
                if response.status == 200:
                    inmemoryfile = io.BytesIO(await response.content.read())
                    if __name__ == "__main__":
                        progress.update(task_id=task, advance=1)
                    return list.append(inmemoryfile)
                else:
                    Console.print(response.status_code, response.url)
                    return

        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[fetch_async(url, session) for url in urls])
            return list


def mtile(h, location):

    shapely.speedups.enable()
    starttime = time.time()
    tile_raster_size = 1000

    x = location[0]
    y = location[1]
    r = location[2]
    tile_buffer = []
    outer_bbox = mdl.setLocation(x, y, r)
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
            + f"SUBSET=x({bbox[0]},{bbox[1]})&SUBSET=y({bbox[2]},{bbox[3]})&OUTFILE=tile{str(i)}.tif"
        )
        urls.append([url, mdl.filename_tile + str(i) + ".tiff"])
    mdl.emptyFolder(mdl.tile_folder)

    def dl():
        for url in urls:
            tile_buffer.append(downloadTiff(url))

    if __name__ == "__main__":
        # with console.status(f"[bold green]Downloading {len(bbox_list)} tile(s)") as s:
        dl()
    else:
        dl()

    downloadtime = time.time()
    arr_list = []

    for tile in tile_buffer:
        with rio.open(tile, "r") as k1:
            arr = k1.read(1)
            bbox = k1.bounds
            transform = k1.transform
            arr_list.append(dict({"arr": arr, "bbox": bbox, "trafo": transform}))
            print(sys.getsizeof(arr_list))
    return


def setLocation(x, y, r):
    """
    get rect raster box of input utm coords
    """
    x = int(x)
    y = int(y)
    r = int(r)
    location = [x - r, x + r, y - r, y + r]
    return location


def loadWFS(wfs_url):
    tile_raster_size = 1000
    outer_bbox = setLocation(370500, 5698700, 2000)
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
    urls = []
    for bbox in bbox_list:
        url = (
            wfs_url
            + f"BBOX={bbox[0]},{bbox[2]},{bbox[1]},{bbox[3]},urn:ogc:def:crs:EPSG::25832"
        )
        urls.append(url)
    tile_buffer = []
    # q = requests.Request("GET", wfs_url).prepare().url
    tile_buffer.extend(asyncio.run(async_download(urls)))
    gdf = 0
    for i in range(len(tile_buffer)):
        if i == 0:
            gdf = gpd.read_file(tile_buffer[0])
        else:
            gdf2 = gpd.read_file(tile_buffer[i])
            gdf = pd.concat([gdf, gdf2])
    res = gdf.to_json()
    gdf.to_file("./output/" + "geb.geojson", driver="GeoJSON")
    return gdf


if __name__ == "__main__":
    location = (370500, 5698700, 2000)
    flood_height = 1
    # mtile(flood_height, location)
    # mdl.createFloodzoneMultiTile(flood_height, location)
    loadWFS(alkis_simplified_wfs_url)
