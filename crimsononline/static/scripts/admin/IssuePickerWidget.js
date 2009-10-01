var set_issue_picker = function(ele, hidden_input, spec_url){
    // turns a date obj into a str of the calendar's format
    var make_datestring = function(date){
        var date_str = (date.getMonth() > 8 ) ? "" : "0";
        date_str += (date.getMonth() + 1) + "/";
        date_str += (date.getDate() > 9) ? "" : "0";
        date_str += date.getDate() + "/" + date.getFullYear();
        return date_str;
    };
    // show / hide different daily / special issue pickers
    $("#issue_picker_meta input").click(function(){
        if($(this).val() == 'daily'){
            $("#issue_picker_daily").show();
            $("#issue_picker_special").hide();
            $(hidden_input).val(
                make_datestring($(ele).datepicker('getDate')));
        } else {
            $("#issue_picker_daily").hide();
            $("#issue_picker_special").show().trigger("change");
        }
    });
    
    // grab list of special issue from server
    $("#issue_picker_special input").change(function(){
        if($(this).val().length == 4){
            var full_url = spec_url + "?year=" + $(this).val();
            $("#issue_picker_special select").load(full_url);
        }
    }).keypress(function(e){
        // prevent enter from submitting the form
        if(e.which == 13){
            $(this).change().blur();
            return false;
        }
    });
    
    $(ele).datepicker({
        showStatus: true,
        showOn: "both",
        buttonImage: "/admin_media/img/admin/icon_calendar.gif",
        buttonImageOnly: true,
        mandatory: true,
        onSelect: function(dateText){
            $(hidden_input).val(dateText);
        }
    });
};