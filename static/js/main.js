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

    $(".download-file").click(onClickDownloadFile);

});

var onClickDownloadFile = function(event){
    var currRow = $(this).parent().parent();
    var fileName = currRow.find('.result-name').textContent;
    var data = {
        "action": "DOWNLOAD",
        "value": fileName
    };
    var json_str = JSON.stringify(data);
    websocket.send(json_str);
};

var hideLoadingAnimation = function(){
    $('#loading-img-container').addClass("hidden");
};

var showLoadingAnimation = function(){
    $('#loading-img-container').removeClass("hidden");
};

var addResult = function(name, date, size){
    var row = '<tr class="result-item">' +
	'<td class="vert-align result-name">' + name + '</td>' +
	'<td class="vert-align result-date">' + date + '</td>' +
	'<td class="vert-align result-size">' + size + '</td>' +
    '<td class="vert-align"><a href="#"><span class="glyphicon glyphicon-download glyphicon-big"></span></a></td>' +
	'</tr>';
};

//var bar = $('div .progress-bar-striped')[0];
//
//$(bar).removeClass('active');
//$(bar).removeClass('progress-bar-striped');