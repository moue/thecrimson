var set_search_choice_field = function(id_prefix, ajax_url){

    var p;  // prefix of all important elements in question
    if(id_prefix[0] == '#') { p = id_prefix; }
    else { p = '#' + id_prefix; }
    
    // set datepickers on date picking items
    $(p + '_wrapper .date_input').datepicker();
    
    // the field where all the values go
    var hidden = $(p + '_wrapper input[type="hidden"]');
    
    // injects a remove button and binds it to remove_content
    var bind_remove = function(ele){
        $('<a class="button remove" href="#">Remove</a>')
            .prependTo(ele)
            .one('click', function(){
                remove_content(ele);
                return false;
            });
    };
    
    // adds the item to the selected items list
    //   also 
    var add_content = function(ele){
        // append value to field
        $(hidden).val($(hidden).val() + ',' + $(ele).data('pk'));
        // inject into DOM
        var target = $(p + '_wrapper .rel_objs');
        ele = $(ele).clone();
        bind_remove(
            $(ele)
                .appendTo(target)
                .hide()
                .slideDown('normal')
        );
    };
    
    // processes the ajax response
    //   dump each object into the results area, bind click handlers, etc
    var process_response = function(url_base, data){
        // dump results into .results and bind click handlers
        var target = $(p + '_wrapper .ajax_search .results');
        $(target).empty();
        if(!data.objs.length){
            $(target).append('<li>No content found.</li>');
        } else {
            $.each(data.objs, function(){
                var ele = $(this[1]);
                $(ele)
                    .appendTo(target)
                    .data('pk', this[0])
                    .one('click', choose_content)
                    .css('cursor', 'pointer')
                    .hover(function(){
                        $(this).css('background-color', '#eeeeee');
                    }, function(){
                        $(this).css('background-color', '');
                    });
                if(already_added(this[0])){ 
                    $(ele)
                        .css('cursor', '')
                        .unbind()
                        .fadeTo('normal', .5);
                }
            });
        }
        // create paging links
        var p_link = (data.prev_page == 0) ? '' : '<a href="#">Prev</a>';
        var n_link = (data.next_page == 0) ? '' : '<a href="#">Next</a>';
        target = $(p + '_wrapper .ajax_search .paging_links');
        $(target).empty();
        if(p_link){
            $(p_link)
                .appendTo(target)
                .click(function(){
                    $.getJSON(url_base + '&page=' + data.prev_page, function(data){
                        process_ajax(url_base, data);
                    })
                    return false;
                });
        }
        $(target).append('&nbsp;');
        if(n_link){
            $(n_link)
                .appendTo(target)
                .click(function(){
                    $.getJSON(url_base + '&page=' + data.next_page + '/', function(data){
                        process_ajax(url_base, data);
                    })
                    return false;
                });
        }
    };
    
    // send ajax search request
    $(p + '_go').click(function(){
        var args = {};
        args.tags = $(p + '_tags').val();
        args.start = $(p + '_start_date').val();
        args.end = $(p + '_end_date').val();
        $.getJSON(ajax_url, args, function(data){
            process_ajax(args, data);
        });
        return false;
    });
    
    
};