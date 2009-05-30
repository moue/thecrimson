$(document).ready(function(){
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