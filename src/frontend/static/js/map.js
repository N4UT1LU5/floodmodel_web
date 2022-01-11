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
var RecFixed, RecUnfixed;
var floodzone_layer, gebOverlap_layer;
var result_layerGroup, outline_layerGroup;
var floodzone_JSON, buildings_JSON;

function initControls() {
    if (mymap) {
        // attribution control - static suffix
        mymap.attributionControl.addAttribution("Flutmodell PoC");

        // scale control
        L.control.scale({ maxWidth: 500, metric: true, imperial: false }).addTo(mymap);

        // layerControl
        myLayerControl = L.control.layers();
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
    var circle;
    if (RecUnfixed) {
        // mymap.removeLayer(RecUnfixed);
        removeNamedLayer(RecUnfixed);
        outline_layerGroup.removeLayer(RecUnfixed);
    }
    if (!lalo) return;
    circle = L.circle(lalo, r, {
        opacity: 0,
        fillOpacity: 0
    }).addTo(mymap);

    recBounds = circle.getBounds();
    removeNamedLayer(circle);

    RecUnfixed = L.rectangle(recBounds, {
        color: "#0000ff",
        weight: 2,
        fillOpacity: 0
    });
    outline_layerGroup.addLayer(RecUnfixed).addTo(mymap);
    myLayerControl.removeLayer(outline_layerGroup);
    myLayerControl.addOverlay(outline_layerGroup, "Umrandung");
}

function fixLocation() {
    if (RecFixed) {
        removeNamedLayer(RecFixed);
        outline_layerGroup.removeLayer(RecFixed);
    }
    // enable request
    document.getElementById("btnFld").disabled = false;

    // set x,y values
    x_fixed = x;
    y_fixed = y;

    RecFixed = L.rectangle(recBounds, {
        color: "#ff0000",
        weight: 3,
        fillOpacity: 0
    });
    outline_layerGroup.addLayer(RecFixed).addTo(mymap);
}

function initMap() {
    // default map frame
    mymap = L.map(mapContainerNodeId, { minZoom: 9 }).setView([51.43, 7.272], 14);
    locateMe();
    mymap.setMaxBounds([
        [52.146, 6.364],
        [50.363, 9.395]
    ]);
    // initialize layergroups
    result_layerGroup = L.layerGroup();
    outline_layerGroup = L.layerGroup();
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
        myLayerControl.removeLayer(layername);
        mymap.removeLayer(layername);
    }
}

function getFloodzone(x, y, r, h) {
    x = parseInt(x * 100000);
    y = parseInt(y * 100000);
    document.getElementById("btnFld").classList.add("btn_loading");
    document.getElementById("btnFld").disabled = true;
    fetch(`http://127.0.0.1:5000/api/createFloodzone?x=${x}&y=${y}&r=${r}&h=${h}`)
        .then((response) => {
            if (response.status === 201) {
                console.log("no river in tile");
                return;
            }
            return response.json();
        })
        .then((data) => {
            if (!data) {
                return;
            }
            floodzone_JSON = data;
            removeNamedLayer(floodzone_layer);
            floodzone_layer = L.geoJSON(data.features);
            floodzone_layer.setStyle({
                color: "#0033ff",
                weight: 2,
                fillColor: "#0033ff",
                fillOpacity: 0.1
            });
            result_layerGroup.addLayer(floodzone_layer).addTo(mymap);
            myLayerControl.addOverlay(floodzone_layer, "Überflutungsgebiet");

            document.getElementById("btnGeb").disabled = false;
        })
        .finally(() => {
            document.getElementById("btnFld").disabled = false;
            document.getElementById("btnFld").classList.remove("btn_loading");
        });
}

function getGebOverlap() {
    document.getElementById("btnGeb").classList.add("btn_loading");
    document.getElementById("btnFld").disabled = true;
    document.getElementById("btnGeb").disabled = true;
    fetch(`http://127.0.0.1:5000/api/createGeb`, {
        method: "post",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(floodzone_JSON)
    })
        .then((response) => {
            if (response.status === 201) {
                console.log("no buildings in tile");
                return;
            }
            return response.json();
        })
        .then((data) => {
            if (!data) {
                return;
            }
            buildings_JSON = data;
            removeNamedLayer(gebOverlap_layer);
            gebOverlap_layer = L.geoJSON(data.features);
            gebOverlap_layer.setStyle({
                color: "#ff3700",
                weight: 1,
                fillColor: "#ff3700",
                fillOpacity: 0.4
            });
            result_layerGroup.addLayer(gebOverlap_layer).addTo(mymap);
            myLayerControl.addOverlay(gebOverlap_layer, "Überflutunge Gebäude");

            document.getElementById("btnGeb").disabled = false;
        })
        .finally(() => {
            document.getElementById("btnFld").disabled = false;
            document.getElementById("btnGeb").classList.remove("btn_loading");
        });
}

function onDomLoaded() {
    initMap();
    // SLIDER JS Waterheight
    let sliderHeight = document.getElementById("height_slider");
    let labelHeight = document.getElementById("height_label_value");
    labelHeight.innerHTML = sliderHeight.value / 10; // Display the default slider value
    h = sliderHeight.value / 10;

    // Update the current slider value (each time you drag the slider handle)
    sliderHeight.oninput = function () {
        labelHeight.innerHTML = this.value / 10;
        h = this.value / 10;
    };

    // SLIDER JS Radius
    let sliderRadius = document.getElementById("radius_slider");
    let labelRadius = document.getElementById("radius_label_value");
    labelRadius.innerHTML = sliderRadius.value * 100; // Display the default slider value
    r = sliderRadius.value * 100;

    // Update the current slider value (each time you drag the slider handle)
    sliderRadius.oninput = function () {
        labelRadius.innerHTML = this.value * 100;
        r = this.value * 100;
        makeTileOutline();
    };

    // Firsttime disable request buttons
    document.getElementById("btnFld").disabled = true;
    document.getElementById("btnGeb").disabled = true;
}

function sendRequestFloodzone() {
    getFloodzone(x_fixed, y_fixed, r, h);
}

function sendRequestGebOverlap() {
    getGebOverlap(x_fixed, y_fixed, r);
}

function donwnloadJSON() {
    if (floodzone_JSON) {
        let data = JSON.stringify(floodzone_JSON);
        const a = document.createElement("a");
        const file = new Blob([data], { type: "text/plain" });
        a.href = URL.createObjectURL(file);
        a.download = "Flutgebiet.json";
        a.click();
    }
    if (buildings_JSON) {
        let data = JSON.stringify(buildings_JSON);
        const a = document.createElement("a");
        const file = new Blob([data], { type: "text/plain" });
        a.href = URL.createObjectURL(file);
        a.download = "Betroffene_Gebaude.json";
        a.click();
    }
}

function zoomToLayer() {
    if (floodzone_layer) {
        mymap.fitBounds(floodzone_layer.getBounds());
    }
}

function zoomInMap() {
    mymap.zoomIn();
}

function zoomOutMap() {
    mymap.zoomOut();
}

function locateMe() {
    mymap.locate({ setView: true, maxZoom: 16 });
}

document.addEventListener("DOMContentLoaded", onDomLoaded);
