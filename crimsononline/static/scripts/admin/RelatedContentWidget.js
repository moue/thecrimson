var set_related_content = function(id_prefix, types){
    var p;
    if(id_prefix[0] == '#') { p = id_prefix; }
    else { p = '#' + id_prefix; }
    $(p + '_wrapper .date_input').datepicker();
    
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
    
    var add_content = function(ct_id, pk, ct_name){
        if(!ct_id){
            ct_id = ct_name
        }
        var url = '/admin/content/rel_content/get/' + ct_id + '/' + pk + '/';
        $.getJSON(url, function(json){
            // append value to field
            ct_id = json.ct_id;
            $(hidden).val($(hidden).val() + ct_id + ',' + pk + ';');
            console.log($(hidden).val());
            // inject into DOM
            json.html = '<li>' + json.html + '</li>';
            var target = $(p + '_wrapper .rel_objs');
            bind_remove(
                $(json.html)
                    .appendTo(target)
                    .hide()
                    .data('rel_ct_id', ct_id)
                    .data('rel_pk', pk)
                    .slideDown('normal')
            );
        }, 'html');
    };
    
    var choose_content = function(){
        add_content($(this).data('rel_ct_id'), $(this).data('rel_pk'));
        $(this)
            .css('cursor', '')
            .css('background-color', '')
            .fadeTo("normal", 0.5)
            .unbind();
    };
    
    var remove_content = function(ele){
        // remove it from the field
        var id = $(ele).data('rel_ct_id') + ',' + $(ele).data('rel_pk');
        var vals = $(hidden).val().split(';');
        var str = '';
        for(var i = 0; i < vals.length; i++){
            if(vals[i] && id!=vals[i]){
                str += vals[i] + ';';
            }
        }
        $(hidden).val(str);
        
        // remove the element
        $(ele).slideUp('normal', function(){
            $(this).remove();
        })
        
        // unfade it in the choices area
        $(p + '_wrapper .ajax_search .results li').each(function(){
            if(id == $(this).data('rel_ct_id') + ',' + $(this).data('rel_pk')){
                $(this)
                    .fadeTo('normal', 1)
                    .css('cursor', 'pointer')
                    .one('click', choose_content)
                    .hover(function(){
                        $(this).css('background-color', '#eeeeee');
                    }, function(){
                        $(this).css('background-color', '');
                    });
            }
        });
    };
    
    // returns true if the content has already been selected
    var already_related = function(ct_id, pk){
        var id = ct_id + ',' + pk
        var arr = $(hidden).val().split(';')
        for(var i = 0; i < arr.length; i++){
            if(arr[i] && id == arr[i]) return true;
        }
        return false;
    };
    
    var process_ajax = function(url_base, data){
        // dump results into .results and bind click handlers
        var target = $(p + '_wrapper .ajax_search .results');
        $(target).empty();
        $.each(data.objs, function(){
            var ele = $(this[2]);
            $(ele)
                .appendTo(target)
                .data('rel_ct_id', this[0])
                .data('rel_pk', this[1])
                .one('click', choose_content)
                .css('cursor', 'pointer')
                .hover(function(){
                    $(this).css('background-color', '#eeeeee');
                }, function(){
                    $(this).css('background-color', '');
                });
            if(already_related(this[0], this[1])){ 
                $(ele)
                    .css('cursor', '')
                    .unbind()
                    .fadeTo('normal', .5);
            }
        });
        if(!data.objs.length){
            $(target).append('<li>No content found.</li>');
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
                    $.getJSON(url_base + data.prev_page + '/', function(data){
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
                    $.getJSON(url_base + data.next_page + '/', function(data){
                        process_ajax(url_base, data);
                    })
                    return false;
                });
        }
    };
    
    // monkey patch dismiss related lookup popup to do a custom insert
    var originalDismissAddAnotherPopup = dismissAddAnotherPopup;
    dismissAddAnotherPopup = function(win, newId, newRepr){
        var matched = '';
        for(var i = 0; i < types.length; i++){
            console.log('id_' + types[i] + ' :: ' + win.name);
            if('id_' + types[i] == win.name){
                matched = types[i];
                break;
            }
        }
        if(matched){
            add_content(0, newId, matched);
            win.close();
        } else {
            return originalDismissAddAnotherPopup(win, newId, newRepr);
        }
    }
    
    
    // make rel objs sortable
    $(p + '_wrapper .rel_objs').sortable({stop: function(){
        // reset value of hidden on sort
        $(hidden).val('');
        $(p + '_wrapper .rel_objs li').each(function(){
            var str = $(this).data('rel_ct_id')+','+$(this).data('rel_pk')+';';
            $(hidden).val($(hidden).val() + str);
        });
    }});
    
    // bind remove buttons and attach rel_content data
    var ids = $(hidden).val().split(';');
    $(p + '_wrapper .rel_objs li').each(function(i){
        id = ids[i].split(',')
        $(this)
            .data('rel_ct_id', id[0])
            .data('rel_pk', id[1]);
        bind_remove(this);
    });
    
    // send ajax search request
    $(p + '_go').click(function(){
        var tags = $(p + '_tags').val();
        var start = $(p + '_start_date').val();
        var end = $(p + '_end_date').val();
        var type = $(p + '_type').val();
        var url = '/admin/content/rel_content/find/' + type + '/' + start + '/' + end + '/' + tags + '/1/';
        $.getJSON(url, function(data){
            process_ajax(url.substr(0, url.length - 2), data);
        });
        return false;
    });
};