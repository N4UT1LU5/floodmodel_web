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
var fixedRectangle;

function initControls() {
  if (mymap) {
    // zoom control as default

    // attribution control - static suffix
    mymap.attributionControl.addAttribution("BO GI II Demo Webapp");

    // scale control
    L.control
      .scale({ maxWidth: 500, metric: true, imperial: false })
      .addTo(mymap);

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

    var wmsLayer_topplus = L.tileLayer.wms(
      "http://sgx.geodatenzentrum.de/wms_topplus_web_open?",
      {
        format: "image/png",
        layers: "web",
        attribution: "&copy; Bundesamt für Kartographie und Geod&auml;sie",
      }
    );

    var wmsLayer_osm = L.tileLayer
      .wms("https://maps.heigit.org/osm-wms/service?", {
        format: "image/png",
        layers: "osm_auto:all",
        attribution:
          '&copy; <a href="www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      })
      .addTo(mymap);

    var wmsLayer_dtk = L.tileLayer.wms(
      "https://www.wms.nrw.de/geobasis/wms_nw_dtk?",
      {
        format: "image/png",
        layers: "nw_dtk_sw",
      }
    );

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

  Rectangle = L.circle();
  function onMapClick(e) {
    lalo = e.latlng;
    var t = document.getElementById("myRange").value * 100;
    var addOnLat = addToLat(t);
    var addOnLng = addToLng(t, lalo.lat + addOnLat);

    circle = L.circle(e.latlng, t, {
      color: "#C02900",
      weight: 1,
      opacity: 0,
      fillColor: "#ff0000",
      fillOpacity: 0,
    }).addTo(mymap);
    recBounds = circle.getBounds();

    console.log(recBounds);

    console.log(recBounds);
    L.rectangle(recBounds, {
      color: "#0000ff",
      weight: 5,
      fillOpacity: 0,
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
}

function sendRequestFloodzone() {
  getFloodzone(x, y, r, h);
}

document.addEventListener("DOMContentLoaded", onDomLoaded);

function fixLocation() {
  fixedRectangle = L.rectangle(recBounds, {
    color: "#ff0000",
    weight: 5,
    fillOpacity: 0,
  });
  fixedRectangle.addTo(mymap);
}
