var braviz = (function(){

//-------------------------------------------
function connect_to_ws(message_handler){
var last_message = null;
var errorSleepTime = 500;
var raw_socket;
 function openWS() {
    var address = "ws://" + window.location.host + "/messages_ws";
    raw_socket = new WebSocket(address);
    raw_socket.onerror=function () {
    if (errorSleepTime < 5000){
    errorSleepTime*=2;
    }
    };
    raw_socket.onmessage = function(e) {
      if (last_message==e.data){
      return;
      }
      var message = JSON.parse(e.data);
      message_handler(message);
      };
      raw_socket.onclose = function(e) {
      window.setTimeout(openWS, errorSleepTime);
    };
  }
  openWS();
  var socket={};
  socket.send = function(msg){
    last_message = msg;
    raw_socket.send(msg);
  };
  return socket;
}

//---------------------------------------------------------------
function configure_variables_and_samples_dialog(button_selector, dialog_selector,
 get_current_cats_trait_ids_sample_id, apply_callback, one_variable,
 disable_samples, disable_categories, disable_traits){

    // TODO: Remove all id selectors

    var dialog = $(dialog_selector);
    var button = $(button_selector);
    function show_variable_select_panel(){

        var cats_vars_traits = get_current_cats_trait_ids_sample_id();
        var traits_indices = cats_vars_traits["trait_indices"].map(function(x){return Number(x);});
        var cats_index = cats_vars_traits["cats_index"];
        var sample_index = cats_vars_traits["sample_index"];

        button.addClass("hidden");
        dialog.removeClass("hidden");

        var vars_list = d3.select("#select-variables-tab div.variable-list");
        var cats_list = d3.select("#categories-list-tab div.variable-list");
        var samples_list = d3.select("#samples-list-tab div.samples-list");

        if(disable_samples){
            $(dialog_selector).find('a[href="#samples-list-tab"]').parent().addClass("hidden");
        }

        if(disable_categories){
            $(dialog_selector).find('a[href="#categories-list-tab"]').parent().addClass("hidden");
        }

        if(disable_traits){
            $(dialog_selector).find('a[href="#select-variables-tab"]').parent().addClass("hidden");
        }

        vars_list.html("");
        cats_list.html("");
        samples_list.html("");

        d3.json("parallel/data/variables_and_samples", function(error,data) {
            if (error){
                alert("Couldn't connect to server, is it running?");
                return;
            }
            //------ variables -------
            var var_data = data["variables"];
            var variables = vars_list.selectAll("div.checkbox").data(var_data);
            var categories = cats_list.selectAll("div.radio").data(var_data.filter(function(e){return e.is_real == 0}));

            var input_type;
            if (one_variable){
                input_type = "radio";
            }
            else{
                input_type = "checkbox";
            }

            variables.enter().append("div").attr("class",input_type)
                .append("label")
                .attr("title", function(d){
                        return d.desc;
                    })
                .call(function(label){
                    label.append("input").attr("type",input_type).attr("name","variable")
                        .attr("value",function(d){return d.index})
                        .attr("checked",function(d){
                            if ((one_variable && traits_indices == d.index)
                                || (!one_variable && (traits_indices.indexOf(d.index)>=0) )){
                                return "checked";
                            }
                          return null;
                        });
                    label.append("p").text(function(d){return d.var_name});
                });

            categories.enter().append("div").attr("class","radio")
                .append("label")
                .attr("title", function(d){return d.desc;})
                .call(function(label){
                    label.append("input").attr("type","radio").attr("name","category")
                        .attr("value",function(d){return d.index})
                        .attr("checked",function(d){
                          if(cats_index == d.index) return "checked";
                          return null;
                        });
                    label.append("p").text(function(d){return d.var_name;});
                });
            //------ samples -------
            var samples_data = data["samples"];
            var samples_items =samples_list.selectAll("div.checkbox").data(samples_data);

            samples_items.enter().append("div").attr("class","radio")
                .append("label")
                .attr("title", function(d){
                        return d.sample_desc;
                    })
                .call(function(label){
                    label.append("input").attr("type","radio").attr("name","sample")
                        .attr("value",function(d){return d.index})
                        .attr("checked",function(d){
                          if(d.index==sample_index) return "checked";
                          return null;
                        });
                    label.append("p").text(function(d){
                        return d.sample_name +" ("+ d.sample_size+ ")";
                    });
                });
            });
    }

    function hide_variable_select_panel(){
    dialog.addClass("hidden");
    button.removeClass("hidden");
    }

    button.click(show_variable_select_panel);
    dialog.find("button.close").click(hide_variable_select_panel);
    dialog.find("#cancel_variable_selection").click(hide_variable_select_panel);

    function filter_variables_list(list, mask){
    mask=mask.toUpperCase();
    $(list).children("div.variable-list div").addClass("hidden");
    $(list).children("div.variable-list div").filter(function (){return this.textContent.toUpperCase().indexOf(mask)>=0 }).removeClass("hidden");
    }

    $("#search-vars").bind("input", function(){
                filter_variables_list($("#select-variables-tab").find("div.variable-list"),
                $("#search-vars").val());
                });

    $("#search-cats").bind("input", function(){
                filter_variables_list($("#categories-list-tab").find("div.variable-list"),
                $("#search-cats").val());
                });

    function clear_list(){
    $("#select-variables-tab").find("div.variable-list input").prop("checked", false);
    }
    $("#clear_checked_variables").click(clear_list);

    $('#variable-control-tabs').find('a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
    });


    function apply_new_variables(){
    var new_cat_idx = $("#categories-list-tab").find("div.variable-list").find("input").filter(function(i,e){return e.checked;}).val();
    var checked_boxes = $("#select-variables-tab").find("div.variable-list").find("input").filter(function(i,e){return e.checked;});
    var selected_sample = $("#samples-list-tab").find("div.samples-list").find("input").filter(function(i,e){return e.checked;}).val();
    var new_trait_indices = checked_boxes.map(function(i, e){return e.value}).toArray();
    if (one_variable){
        new_trait_indices = new_trait_indices[0];
    }

    apply_callback(new_cat_idx, new_trait_indices, selected_sample);
    hide_variable_select_panel();
    }
    $("#apply-variable-change").click(apply_new_variables);


}
//---------------------EXPORT-------------------------------------

var braviz_module = {};
braviz_module.connect_to_ws = connect_to_ws;
braviz_module.configure_variables_and_samples_dialog = configure_variables_and_samples_dialog;
return braviz_module;
})();