
$(document).ready(function (){
    if($("#add_id_contributors").length){
        $("#add_id_contributors").tooltip({
            bodyHandler: function(){
                return $("<span>").html("Create a new Contributor");
            },
            showURL: false,
            delay: 50
        });
    }
});