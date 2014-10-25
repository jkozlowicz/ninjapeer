$(document).ready(function(){
    init();

    $("#query-form").submit(onClickSearch);
    $('body').on("click", "table tbody tr td a", onClickDownloadFile);
    $(".stop-download-file").click(onClickStopDownloadFile);
    $(".delete-file").click(onClickDeleteFile);
    $("#download-pause-btn").click(onClickPauseBtn);
    $("#download-resume-btn").click(onClickResumeBtn);
    $("#download-remove-btn").click(onClickRemoveBtn);
    initDownloadProgressTable();

});

var focusedDownloadRowHash = null;

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

        var fileSize = formatFileSize(result.size);

        var row = '<tr class="result-item">' +
        '<td class="vert-align result-name">' + result.name + '</td>' +
        '<td class="vert-align result-hash">' + result.hash + '</td>' +
//        '<td class="vert-align result-date">' + result.date + '</td>' +
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
        fileSize = intPart.concat(".", decimalPart);
    }
    return fileSize + ' ' + unit;
};

var ifAlreadyInResult = function(hash){
    return $("#query-result-table td").filter(function() {
        return $(this).text() == hash;
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

var renderProgress = function(transfers){
    for(var i=0; i<transfers.length; i++){

        var tableRow = $('td.transfer-hash').filter(function() {
            return $(this).text() == transfers[i].hash;
        }).closest("tr");

        if(tableRow.length > 0){
            updateProgressRow(tableRow, transfers[i]);
        }else{
            appendProgressRow(tableRow, transfers[i]);
        }

        var detailsHashElement = $('dd.item-details-hash').filter(function() {
            return $(this).text() == transfers[i].hash;
        });

        if(detailsHashElement.length > 0){
            displayItemDetails(transfers[i]);
        }

    }
};

var capitalize = function(s){
    return s[0].toUpperCase() + s.slice(1).toLowerCase();
};

var updateProgressRow = function(row, transfer){
//progress-bar-warning
    $(row).find('.transfer-name').text(transfer['file_name']);
    $(row).find('.transfer-size').text(
        formatFileSize(transfer['size'])
    );
    $(row).find('.transfer-status').text(capitalize(transfer['status']));

    if(transfer['status'] === 'FINISHED'){
        $(row).find('.transfer-download-rate').text('-');
        $(row).find('.transfer-eta').text('-');
    }else{
        $(row).find('.transfer-download-rate').text(transfer['download_rate']);
        $(row).find('.transfer-eta').text(transfer['ETA']);
    }
    $(row).find('.transfer-added-on').text(transfer['added_on']);
    $(row).find('.transfer-hash').text(transfer['hash']);

    updateProgressBar(row, transfer['progress']);

    var numOfChunks = transfer['num_of_chunks'].toString();
    var currChunk = transfer['curr_chunk'].toString();
    var chunkSize = formatFileSize(transfer['chunk_size']);

    $(row).find('.transfer-chunk-size').text(chunkSize);
    $(row).find('.transfer-save-as').text(transfer['path']);
    $(row).find('.transfer-wasted').text(transfer['wasted']);
    $(row).find('.transfer-time-elapsed').text(transfer['time_elapsed']);
    $(row).find('.transfer-pieces').text(
            numOfChunks + ' x ' + chunkSize + '(have ' + currChunk + ')'
    );
    $(row).find('.transfer-downloaded').text(
        formatFileSize(transfer['bytes_received'])
    );
    $(row).removeClass('hidden');
};

var updateProgressBar = function(row, value){
    var $progressBar = $(row).find('.progress-bar');
    $progressBar.attr('style', 'width: ' + value.toString() + '%');
    $progressBar.attr('aria-valuenow', value);
};

var appendProgressRow = function(row, transfer){
    var $tr = $('tr.home-item:last');
    var $clone = $tr.clone();
    $tr.after($clone);
    updateProgressRow($clone, transfer);
};

var initDownloadProgressTable = function(){
    var $table = $('#home-items-table');
    $table.floatThead({
        scrollContainer: function($table){
            return $table.closest('#download-progress-table-wrapper');
        }
    });


    $('body').on("click", "#home-items-table tr", onClickDownloadRow);
//    $('#home-items-table tr').click(onClickDownloadRow);
};

var onClickDownloadRow = function(){
    var hash = $(this).find('td.transfer-hash').text();
    var status = $(this).find('td.transfer-status').text().toLowerCase();
    focusedDownloadRowHash = hash;
    $("#home-items-table tr").removeClass("highlight");
    $(this).addClass("highlight");
    enableButtons(status);

    for(var i=0; i<downloadTransfers.length ; i++){
        if(hash === downloadTransfers[i].hash){
            displayItemDetails(downloadTransfers[i]);
            break;
        }
    }

};

var displayItemDetails = function(transfer){

    $('.item-details-downloaded').text(formatFileSize(transfer['bytes_received']));
    $('.item-details-piece-size').text(formatFileSize(transfer['chunk_size']));
    $('.item-details-total-size').text(formatFileSize(transfer['size']));

    $('.item-details-time-elapsed').text(transfer['time_elapsed']);
    $('.item-details-status').text(transfer['status']);

    if(transfer['status'] === 'FINISHED'){
        $('.item-details-eta').text('-');
        $('.item-details-download-rate').text('-');
    }else{
        $('.item-details-eta').text(transfer['ETA']);
        $('.item-details-download-rate').text(transfer['download_rate']);
    }

    var numOfChunks = transfer['num_of_chunks'].toString();
    var currChunk = transfer['curr_chunk'].toString();
    var chunkSize = formatFileSize(transfer['chunk_size']);
    $('.item-details-pieces').text(
            numOfChunks + ' x ' + chunkSize + ' (have ' + currChunk + ')'
    );

    $('.item-details-wasted').text(transfer['wasted'] + ' checksum failed');
    $('.item-details-name').text(transfer['file_name']);
    $('.item-details-save-as').text(transfer['path']);
    $('.item-details-hash').text(transfer['hash']);
    $('.item-details-added-on').text(transfer['added_on']);

    var $progressBar = $('.item-details-progress-bar');
    var $progressBarClone = $progressBar.clone();
    $progressBar.attr('style', 'width: ' + transfer['progress'].toString() + '%');
    $progressBar.attr('aria-valuenow', transfer['progress']);
    $progressBar.removeClass('hidden');

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

var onClickPauseBtn = function(){
    sendAction("PAUSE", focusedDownloadRowHash);
    enableResumeBtn();
    disablePauseBtn();
};

var onClickResumeBtn = function(){
    sendAction("RESUME", focusedDownloadRowHash);
    enablePauseBtn();
    disableResumeBtn();
};

var onClickRemoveBtn = function(){
    var confirmed = confirm("Are you sure?");
    if(confirmed){
        sendAction("REMOVE", focusedDownloadRowHash);
    }
};




















