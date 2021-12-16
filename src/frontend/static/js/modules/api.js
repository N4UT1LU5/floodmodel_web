function getFloodzone(x, y, r, h) {
    fetch(`http://127.0.0.1:5000/api/createFloodzone?x=${x}&y=${y}&r=${r}&h=${h}`)
        .then((response) => response.json())
        .then((data) => console.log(data));
}
