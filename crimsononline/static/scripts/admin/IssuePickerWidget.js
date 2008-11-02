/*Game plan:
 on month change, ask server for days in that month for which issues exist.
 go through and highlight them all in the calendar.
 on select, convert into an issue.
 
 server should return a dictionary of date / issue pairs
*/

var inspect = function(obj){
    var str = ""
    for(x in obj){
        str += x + ": " + obj[x] + "\n";
    }
    return str;
}

var set_issue_picker = function(ele, hidden_input, url){
    var issueDays = {
        '08/01/2008': 4,
    }
    var highlight_calendar = function(date){
        $(".ui-datepicker-days-cell a").each(function(i){
            var issue_id = 0;
            var date_str = (date.getMonth() > 8 ) ? "" : "0";
            date_str += (date.getMonth() + 1) + "/";
            date_str += ($(this).html() > 9) ? "" : "0";
            date_str += $(this).html() + "/" + date.getFullYear();
            if(issue_id = issueDays[date_str]){
                $(this).addClass("ui-datepicker-has-issue");
            }
        });
    }
    // show / hide different daily / special issue pickers
    $("#issue_picker_meta input").change(function(){
        if($(this).val() == 'daily'){
            $("#issue_picker_daily").show();
            $("#issue_picker_special").hide();
        } else {
            $("#issue_picker_daily").hide();
            $("#issue_picker_special").show();
        }
    })
    
    $(ele).datepicker({
        showOn: "button",
        buttonImage: "/media/img/admin/icon_calendar.gif",
        buttonImageOnly: true,
        mandatory: true,
        // convert to issue_id.
        onSelect: function(dateText){
            var issue_id = 0;
            if(issue_id = issueDays[dateText]){
                $(hidden_input).val(issue_id);
            }
        },
        // ask server for list of date - issues
        onChangeMonthYear: function(date){
            $.getJSON(url, 
                {
                    year: date.getFullYear(), 
                    month: date.getMonth() + 1,
                }, 
                function(data){
                    // append to the issueDays array
                    $.extend(issueDays, data);
                    // highlight the calendar days with issues
                    highlight_calendar(date);
                }
            )
        },
    });
}