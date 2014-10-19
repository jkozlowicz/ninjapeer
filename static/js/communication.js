var websocket = null;

function init() {

    $.get("http://localhost:8000/gethost", function(data){
        var host = $.parseJSON(data).host;
        var websockAddr = "ws://" + host + ":8888";
        console.log(websockAddr);
        websocket = new WebSocket(websockAddr);
        websocket.onopen = function(e) { onOpen(e) };
        websocket.onmessage = function(e) { onMessage(e) };
        websocket.onerror = function(evt) { onError(evt) };
    });
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
    console.log(e.data);
    var msg = $.parseJSON(e.data);
    if(msg.event == 'MATCH'){

        renderMatchResult(msg.content);

    }
}