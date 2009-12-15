$(document).ready(function(){

    $("form").submit(function(){
        // don't bother prompting if they're not trying to send this
        if(!$("#id_send").val()){
            return true;
        }
        
        // prompt user before send
        num_cat = ("" + $("#id_categories").val()).split(",").length;
        prompt = "Warning, this email will be sent to " + num_cat + " categories. Proceed?";
        if(confirm(prompt) == true){
            return true;
        }
        return false;
    });
});