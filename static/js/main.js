$(document).ready(function(){
    init();

    $("#query-form").submit(onClickSearch);
    $('body').on("click", "table tbody tr td a", onClickDownloadFile);
    $(".stop-download-file").click(onClickStopDownloadFile);
    $(".delete-file").click(onClickDeleteFile);
    initDownloadProgressTable();

});

var getFileDetails = function(elem){
    /** currRow stores reference to parent <tr> element*/
    var currRow = $(elem).parent().parent();
    return {
        "fileName": currRow.find('.result-name')[0].textContent,
        "hash": currRow.find('.result-hash')[0].textContent
    };
};

var onClickSearch = function(event){
    hideResultTable();
    var query = $( "#inputQuery" ).val();
    if ((query !== "" &&  query !== undefined)) {
        sendAction("QUERY", query);
        clearMatchResult();
        showLoadingAnimation();
    }else{
        //TODO: Display error
    }
    event.preventDefault();
};

var onClickStopDownloadFile = function(){
    sendAction("STOP_DOWNLOAD", getFileDetails(this));
};

var onClickDeleteFile = function(){
    sendAction("DELETE_FILE", getFileDetails(this));
};

var onClickDownloadFile = function(){
    sendAction("DOWNLOAD", getFileDetails(this));
};

var sendAction = function(action, value){
    var data = {
        "action": action,
        "value": value
    };
    var json_str = JSON.stringify(data);
    websocket.send(json_str);
};

var renderMatchResult = function(lastMatchResult){
    showResultTable();
    var matchResultTableBody = $('#query-result-table tbody');
    for(var i=0; i<lastMatchResult.length ; i++){
        var result = lastMatchResult[i];
        if(ifAlreadyInResult(result.hash) > 0){
            continue;
        }

        var fileSize = formatFileSize(result);

        var row = '<tr class="result-item">' +
        '<td class="vert-align result-name">' + result.name + '</td>' +
        '<td class="vert-align result-hash">' + result.hash + '</td>' +
        '<td class="vert-align result-date">' + result.date + '</td>' +
        '<td class="vert-align result-size">' + fileSize + '</td>' +
        '<td class="vert-align"><a href="#"><span class="glyphicon glyphicon-download glyphicon-big"></span></a></td>' +
        '</tr>';
        matchResultTableBody.append(row);
    }
};
//var bar = $('div .progress-bar-striped')[0];
//
//$(bar).removeClass('active');
//$(bar).removeClass('progress-bar-striped');

var formatFileSize = function(fileSizeTuple){
    var fileSize = fileSizeTuple[0];
    var unit = fileSizeTuple[1];
    fileSize = fileSize.toString();
    var maxLetters = 6;
    if(fileSize.length > maxLetters){
        var fileSizeSplit = fileSize.split(".");
        var intPart = fileSizeSplit[0];
        var decimalPart = fileSizeSplit[1];
        decimalPart = decimalPart.substring(0, 2);
        return intPart.concat(".", decimalPart)
    }
    return fileSize + ' ' + unit;
};

//TODO: poprawić to, bo jest zahardcodeowane
var ifAlreadyInResult = function(hash){
    return $("#query-result-table td").filter(function() {
        return $(this).text() == "8358ac84b43444c8f893d07681bbbf6d";
    }).length;
};

var hideLoadingAnimation = function(){
    $('#loading-img-container').addClass("hidden");
};

var showLoadingAnimation = function(){
    $('#loading-img-container').removeClass("hidden");
};

var hideResultTable = function(){
    $('#query-result-table-container').addClass("hidden");
};

var showResultTable = function(){
    $('#query-result-table-container').removeClass("hidden");
};

var clearMatchResult = function(){
    $('#query-result-table tbody').empty();
};

var requestLastQueryResult = function(){
    sendAction("LAST_QUERY_RESULT", null);
};

var renderProgress = function(msg){
    console.log(msg);
};

var initDownloadProgressTable = function(){
    var $table = $('#home-items-table');
    $table.floatThead({
        scrollContainer: function($table){
            return $table.closest('#download-progress-table-wrapper');
        }
    });

    $('#home-items-table tr').click(onClickDownloadRow);
};

var onClickDownloadRow = function(){
    var hash = $(this).find('td.transfer-hash').text();
    var status = $(this).find('td.transfer-status').text().toLowerCase();
    $("#home-items-table tr").removeClass("highlight");
    $(this).addClass("highlight");
    displayItemDetails(hash);
    enableButtons(status);
};

var enableButtons = function(status){
    if(status == 'downloading'){
        enablePauseBtn();
        enableRemoveBtn();
        disableResumeBtn();
    }else if(status == 'paused'){
        enableResumeBtn();
        enableRemoveBtn();
        disablePauseBtn();
    }else if(status == 'finished'){
        disablePauseBtn();
        disableResumeBtn();
        enableRemoveBtn();
    }else{
        disablePauseBtn();
        disableResumeBtn();
        disableRemoveBtn();
    }
};

var displayItemDetails = function(hash){

};

var enableResumeBtn = function(){
    $('#download-resume-btn').prop('disabled', false);
};

var enablePauseBtn = function(){
    $('#download-pause-btn').prop('disabled', false);
};

var enableRemoveBtn = function(){
    $('#download-remove-btn').prop('disabled', false);
};

var disableResumeBtn = function(){
    $('#download-resume-btn').prop('disabled', true);
};

var disablePauseBtn = function(){
    $('#download-pause-btn').prop('disabled', true);
};

var disableRemoveBtn = function(){
    $('#download-remove-btn').prop('disabled', true);
};























