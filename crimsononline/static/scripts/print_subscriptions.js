$(document).ready(function(){
    $("select[name=sub_type]").change(function(){
        read_type();
    });
    
    $("select[name=start_period]").change(function(){
        read_price();
    });
    
    function read_price(){
        cur_type = $("select[name=sub_type]").val();
        cur_start = $("select[name=start_period]").val();
        if(cur_type && cur_start && prices[cur_type][cur_start]){
            $("span.subscription_price").html("$" + prices[cur_type][cur_start]);
            $("button[type=submit]").removeAttr('disabled');
            // stuff for paypal
            $("input[name=amount]").val(prices[cur_type][cur_start]);
            var item = types[cur_type] + " Subscription to The Harvard Crimson, starting in " + start_dates[cur_start];
            $("input[name=item_name]").val(item);
        }
        else{
            $("span.subscription_price").html("");        
            $("button[type=submit]").attr("disabled","disabled");
        }        
    }
    function read_type(){
        cur_type = $("select[name=sub_type]").val()
        options = '<option selected="selected" value="">---------</option>';
        if(!cur_type){
            $("select[name=start_period]").html(options);
            read_price();
            return;
        }
        for(i=0; i<start_dates.length; i++){
            if(prices[cur_type][i]){
                key = start_dates[i];
                val = i;
                options = options + '<option value="' + val + '">' + key + '</option>';
            }
        }
        $("select[name=start_period]").html(options);
        $("span.subscription_price").html("")
        read_price();
    }
    read_type();
});