$(document).ready(function(){
    init();

    $("#query-form").submit(function( event ) {
        var query = $( "#inputQuery" ).val();
        if ((query !== "" &&  query !== undefined)) {
            var data = {
                "action": "QUERY",
                "value": query
            };
            var json_str = JSON.stringify(data);
            websocket.send(json_str);
            showLoadingAnimation();
        }else{
            //TODO: Display error
        }
        event.preventDefault();
    });

});

var hideLoadingAnimation = function(){
    $('#loading-img-container').addClass("hidden");
}

var showLoadingAnimation = function(){
    $('#loading-img-container').removeClass("hidden");
}