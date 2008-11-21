/*Game plan:
 on month change, ask server for days in that month for which issues exist.
 go through and highlight them all in the calendar.
 on select, send datestring to the hidden input.
 
 server should return a dictionary of date / issue pairs
*/


var inspect = function(obj){
    var str = ""
    for(x in obj){
        str += x + ": " + obj[x] + "\n";
    }
    return str;
};

var set_issue_picker = function(ele, hidden_input, url, spec_url){
    var issueDays = {
        '08/01/2008': 4
    };
    var make_datestring = function(date){
        var date_str = (date.getMonth() > 8 ) ? "" : "0";
        date_str += (date.getMonth() + 1) + "/";
        date_str += (date.getDate() > 9) ? "" : "0";
        date_str += date.getDate() + "/" + date.getFullYear();
        return date_str
    };
    var highlight_calendar = function(date){
        $(".ui-datepicker-days-cell a").each(function(i){
            var issue_id = 0;
            var date_str = make_datestring(date);
            if(issue_id = issueDays[date_str]){
                $(this).addClass("ui-datepicker-has-issue");
            }
        });
    };
    // show / hide different daily / special issue pickers
    $("#issue_picker_meta input").change(function(){
        if($(this).val() == 'daily'){
            $("#issue_picker_daily").show();
            $("#issue_picker_special").hide();
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
        /*statusForDate: function(date){
            if(! issueDays[make_datestring(date)]){
                return "Create a new issue.";
            } else {
                return "There are other articles in this issue.";
            }
        },*/
        showOn: "both",
        buttonImage: "/media/img/admin/icon_calendar.gif",
        buttonImageOnly: true,
        mandatory: true,
        onSelect: function(dateText){
            $(hidden_input).val(dateText);
        },
        // ask server for list of date - issues
        /*onChangeMonthYear: function(date){
            $.getJSON(
                url, 
                {
                    year: date.getFullYear(), 
                    month: date.getMonth() + 1
                }, 
                function(data){
                    // append to the issueDays array
                    $.extend(issueDays, data);
                    // highlight the calendar days with issues
                    //highlight_calendar(date);
                }
            )
        }*/
    });
    
    // before form submit, make sure hidden input matches selected
    $("#article_form").submit(function(){
        if($("#issue_picker_meta input").val() == "daily"){
            $(hidden_input).val($(ele).val());
        } else {
            $(hidden_input).val($("#issue_picker_special select").val());
        }
        return true;
    });
};