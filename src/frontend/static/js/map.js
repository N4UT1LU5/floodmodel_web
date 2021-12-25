// import { getFloodzone } from "./modules/api.js";

var mapContainerNodeId = "mapContainer";

var mymap;
var myLayerControl;
var x = 0;
var y = 0;
var h = 1;
var r = 1000;
var lalo = 0;
var radius = 0;
var recBounds = [];
var mymap;
var circle;
var RecFixed;

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

        var wmsLayer_topplus = L.tileLayer.wms("http://sgx.geodatenzentrum.de/wms_topplus_web_open?", {
            format: "image/png",
            layers: "web",
            attribution: "&copy; Bundesamt für Kartographie und Geod&auml;sie"
        });

        var wmsLayer_osm = L.tileLayer
            .wms("https://maps.heigit.org/osm-wms/service?", {
                format: "image/png",
                layers: "osm_auto:all",
                attribution: '&copy; <a href="www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            })
            .addTo(mymap);

        var wmsLayer_dtk = L.tileLayer.wms("https://www.wms.nrw.de/geobasis/wms_nw_dtk?", {
            format: "image/png",
            layers: "nw_dtk_sw"
        });

        // add baseLayers to Base Layers in layer control
        myLayerControl.addBaseLayer(wmsLayer_topplus, "TopPlus WMS");
        myLayerControl.addBaseLayer(wmsLayer_osm, "OSM WMS");
        myLayerControl.addBaseLayer(wmsLayer_dtk, "DTK WMS");
    }
}

function initMap() {
    mymap = L.map(mapContainerNodeId).setView([51.461372, 7.2418863], 12);

    initControls();

    initBackgroundLayers();
    let RecUnfixed;
    Rectangle = L.circle();
    function onMapClick(e) {
        lalo = e.latlng;
        var t = document.getElementById("myRange").value * 100;

        circle = L.circle(e.latlng, t, {
            color: "#C02900",
            weight: 1,
            opacity: 0,
            fillColor: "#ff0000",
            fillOpacity: 0
        }).addTo(mymap);
        recBounds = circle.getBounds();
        // console.log(RecUnfixed);
        if (RecUnfixed) {
            mymap.removeLayer(RecUnfixed);
        }
        RecUnfixed = L.rectangle(recBounds, {
            color: "#0000ff",
            weight: 5,
            fillOpacity: 0
        }).addTo(mymap);
    }

    mymap.on("click", onMapClick);
}

function getFloodzone(x, y, r, h) {
    fetch(`http://127.0.0.1:5000/api/createFloodzone?x=${x}&y=${y}&r=${r}&h=${h}`)
        .then((response) => response.json())
        .then((data) => {
            console.log(data.features);
            L.geoJSON(data.features).addTo(mymap);
        });
}

function onDomLoaded() {
    initMap();
    // SLIDER JS Waterheight
    var sliderWater = document.getElementById("myHeight");
    var outputWater = document.getElementById("demowater");
    outputWater.innerHTML = document.getElementById("myHeight").value; // Display the default slider value

    // Update the current slider value (each time you drag the slider handle)
    sliderWater.oninput = function () {
        outputWater.innerHTML = this.value;
        waterheight = this.value;
    };
    // SLIDER JS Radius
    var slider = document.getElementById("myRange");
    var output = document.getElementById("demoradius");
    output.innerHTML = document.getElementById("myRange").value; // Display the default slider value

    // Update the current slider value (each time you drag the slider handle)
    slider.oninput = function () {
        output.innerHTML = this.value * 100;
        radius = this.value * 100;
    };
}

function sendRequestFloodzone() {
    getFloodzone(x, y, r, h);
}

document.addEventListener("DOMContentLoaded", onDomLoaded);

function fixLocation() {
    if (RecFixed) {
        mymap.removeLayer(RecFixed);
    }
    RecFixed = L.rectangle(recBounds, {
        color: "#ff0000",
        weight: 5,
        fillOpacity: 0
    });
    RecFixed.addTo(mymap);
}
