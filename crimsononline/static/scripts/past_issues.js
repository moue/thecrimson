$(document).ready(function(){
    days_html();

    $("#past_issues_button").click(function(){
        url = window.location.href;
        issue_position = url.search("issue");
        if(issue_position != -1)
            url = url.substring(0, issue_position)
        month = $("select[name=past_issues_0]").val();
        day = $("select[name=past_issues_1]").val();
        year = $("select[name=past_issues_2]").val();
        add_to = "issue/" + month + "/" + day + "/" + year + "/";
        window.location = url + add_to;
    });
});
$("select[name=past_issues_0]").change(function(){days_html()});
$("select[name=past_issues_2]").change(function(){days_html()});

function days_html(){
    prev_day = $("select[name=past_issues_1]").val();
    month = $("select[name=past_issues_0]").val();
    year = $("select[name=past_issues_2]").val();
    $("select[name=past_issues_1]").html(generate_days_list(days_in_month(month, year)));
    $("select[name=past_issues_1]").val(prev_day);
}

function generate_days_list(days){
    ret_val = ""
    for(i = 1; i <= days; i++){
        ret_val += '<option value="' + i + '">' + i + '</option>\n'
    }
    return(ret_val);
}

function days_in_month(month, year){return 32 - new Date(year, month - 1, 32).getDate();}