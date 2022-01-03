// import { getFloodzone } from "./modules/api.js";

var mapContainerNodeId = "mapContainer";

var mymap;
var myLayerControl;
var x = 0;
var y = 0;
var x_fixed = x;
var y_fixed = y;
var h = 1;
var r = 1000;
var lalo;
var recBounds = [];
var circle;
var RecFixed;
var RecUnfixed;
var floodzone_layer;
var gebOverlap_layer;
var result_layerGroup;

function initControls() {
    if (mymap) {
        // zoom control as default

        // attribution control - static suffix
        mymap.attributionControl.addAttribution("BO GI II Demo Webapp");

        // scale control
        L.control.scale({ maxWidth: 500, metric: true, imperial: false }).addTo(mymap);

        // layerControl
        var baseLayers = {};
        var overlayLayers = {};
        myLayerControl = L.control.layers(baseLayers, overlayLayers);
        myLayerControl.addTo(mymap);
    }
}

function initBackgroundLayers() {
    if (mymap && myLayerControl) {
        // specify all background WMS layers
        // only OSM as active layer
        //https://leaflet-extras.github.io/leaflet-providers/preview/
        var wmsLayer_topplus = L.tileLayer.wms("http://sgx.geodatenzentrum.de/wms_topplus_web_open?", {
            format: "image/png",
            layers: "web",
            attribution: "&copy; Bundesamt für Kartographie und Geod&auml;sie"
        });

        var wmsLayer_osm = L.tileLayer("https://{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(mymap);

        var wmsLayer_dtk = L.tileLayer.wms("https://www.wms.nrw.de/geobasis/wms_nw_dtk?", {
            format: "image/png",
            layers: "nw_dtk_sw"
        });
        var Esri_WorldImagery = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                attribution:
                    "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
            }
        );

        // add baseLayers to Base Layers in layer control
        myLayerControl.addBaseLayer(wmsLayer_osm, "OSM");
        myLayerControl.addBaseLayer(wmsLayer_topplus, "TopPlus WMS");
        myLayerControl.addBaseLayer(wmsLayer_dtk, "DTK WMS");
        myLayerControl.addBaseLayer(Esri_WorldImagery, "Luftbild");
    }
}

function makeTileOutline() {
    if (RecUnfixed) {
        mymap.removeLayer(RecUnfixed);
    }
    circle = L.circle(lalo, r, {
        color: "#C02900",
        weight: 1,
        opacity: 0,
        fillColor: "#ff0000",
        fillOpacity: 0
    }).addTo(mymap);

    recBounds = circle.getBounds();
    removeNamedLayer(RecUnfixed);
    RecUnfixed = L.rectangle(recBounds, {
        color: "#0000ff",
        weight: 5,
        fillOpacity: 0
    }).addTo(mymap);
}

function initMap() {
    mymap = L.map(mapContainerNodeId).setView([51.430887039964055, 7.27251886572458], 14);
    result_layerGroup = L.layerGroup();

    initControls();
    initBackgroundLayers();

    mymap.on("click", onMapClick);
}

function onMapClick(e) {
    lalo = e.latlng;
    x = lalo.lat;
    y = lalo.lng;
    makeTileOutline();
}

function removeNamedLayer(layername) {
    if (layername) {
        result_layerGroup.removeLayer(layername);
    }
}

function getFloodzone(x, y, r, h) {
    x = parseInt(x * 100000);
    y = parseInt(y * 100000);
    fetch(`http://127.0.0.1:5000/api/createFloodzone?x=${x}&y=${y}&r=${r}&h=${h}`)
        .then((response) => response.json())
        .then((data) => {
            // console.log(data.features);
            removeNamedLayer(floodzone_layer);
            floodzone_layer = L.geoJSON(data.features);
            result_layerGroup.addLayer(floodzone_layer).addTo(mymap);
        });
}

function getGebOverlap(x, y, r) {
    x = parseInt(x * 100000);
    y = parseInt(y * 100000);
    fetch(`http://127.0.0.1:5000/api/createGeb?x=${x}&y=${y}&r=${r}`)
        .then((response) => response.json())
        .then((data) => {
            // console.log(data.features);
            removeNamedLayer(gebOverlap_layer);
            gebOverlap_layer = L.geoJSON(data.features);
            gebOverlap_layer.setStyle({
                color: "#fff200",
                weight: 1,
                // opacity: 0,
                fillColor: "#fff300"
                // fillOpacity: 0
            });
            result_layerGroup.addLayer(gebOverlap_layer).addTo(mymap);
        });
}

function onDomLoaded() {
    initMap();
    // SLIDER JS Waterheight
    let sliderWater = document.getElementById("height_slider");
    let outputWater = document.getElementById("height_label_value");
    outputWater.innerHTML = document.getElementById("height_slider").value; // Display the default slider value

    // Update the current slider value (each time you drag the slider handle)
    sliderWater.oninput = function () {
        outputWater.innerHTML = this.value;
        h = this.value;
    };
    // SLIDER JS Radius
    let sliderRadius = document.getElementById("radius_slider");
    let outputRadius = document.getElementById("radius_label_value");
    outputRadius.innerHTML = document.getElementById("radius_slider").value * 100; // Display the default slider value

    // Update the current slider value (each time you drag the slider handle)
    sliderRadius.oninput = function () {
        outputRadius.innerHTML = this.value * 100;
        r = this.value * 100;
        makeTileOutline();
    };
}

function sendRequestFloodzone() {
    getFloodzone(x_fixed, y_fixed, r, h);
}

function sendRequestGebOverlap() {
    getGebOverlap(x_fixed, y_fixed, r);
}

function fixLocation() {
    if (RecFixed) {
        mymap.removeLayer(RecFixed);
    }
    // set x,y values
    x_fixed = x;
    y_fixed = y;

    RecFixed = L.rectangle(recBounds, {
        color: "#ff0000",
        weight: 5,
        fillOpacity: 0
    });
    RecFixed.addTo(mymap);
}

document.addEventListener("DOMContentLoaded", onDomLoaded);
