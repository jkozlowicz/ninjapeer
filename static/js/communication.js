var websockAddr = "ws://" + window.location.hostname + ":8888";
var websocket = null;
var downloadTransfers = [];

function init() {
    websocket = new WebSocket(websockAddr);
    websocket.onopen = function(e) { onOpen(e) };
    websocket.onmessage = function(e) { onMessage(e) };
    websocket.onerror = function(evt) { onError(evt) };
}

function onError(evt){
    console.log(evt.data);
}

function onOpen(e) {
    if(window.location.pathname === '/search'){
        requestLastQueryResult();
    }else if(window.location.pathname === '/home'){
        console.log('home');
    }
}

function onMessage(e) {
//    console.log(e.data);
    var msg = $.parseJSON(e.data);
    if(msg.event == 'MATCH'){

        renderMatchResult(msg.content);

    }else if(msg.event == 'PROGRESS'){

        renderProgress(msg.content);
        downloadTransfers = msg.content;

    }
}