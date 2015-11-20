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
function configure_variables_and_samples_dialog(
    get_current_values,
    apply_callback,
    options
    ){

    var disable_sample = true;
    var disable_category = true;
    var disable_variables = false;
    var disable_subject = true;
    var multiple_variables = false;

    if (options["disable_sample"] !== undefined){
        disable_sample = options["disable_sample"];
    }

    if (options["disable_variables"] !== undefined){
        disable_variables = options["disable_variables"];
    }

    if (options["disable_category"] !== undefined){
        disable_category = options["disable_category"];
    }

    if (options["disable_subject"] !== undefined){
        disable_subject = options["disable_subject"];
    }

    if (options["multiple_variables"] !== undefined){
        multiple_variables = options["multiple_variables"];
    }

    var dialog = $("#bvz-variable-select-panel");
    var button = $("#bvz-change-vars-buttons");
    function show_variable_select_panel(){

        var current_values = get_current_values();
        var variables_indices = current_values["variables_indices"];
        if (multiple_variables){
            variables_indices=variables_indices.map(function(x){return Number(x);});
        }
        else{
            variables_indices=Number(variables_indices);
        }
        var cats_index = current_values["category_index"];
        var sample_index = current_values["sample_index"];
        var subject_index = current_values["subject_index"];

        button.addClass("hidden");
        dialog.removeClass("hidden");

        var vars_list = d3.select("#bvz-variables-list-tab div.variable-list");
        var cats_list = d3.select("#bvz-category-list-tab div.variable-list");
        var samples_list = d3.select("#bvz-samples-list-tab div.samples-list");
        var subjects_list = d3.select("#bvz-subjects-list-tab div.subjects-list");

        if(disable_sample){
            dialog.find('a[href="#bvz-samples-list-tab"]').parent().addClass("hidden");
        }

        if(disable_category){
            dialog.find('a[href="#bvz-category-list-tab"]').parent().addClass("hidden");
        }

        if(disable_variables){
            dialog.find('a[href="#bvz-variables-list-tab"]').parent().addClass("hidden");
        }

        if(disable_subject){
            dialog.find('a[href="#bvz-subjects-list-tab"]').parent().addClass("hidden");
        }

        vars_list.html("");
        cats_list.html("");
        samples_list.html("");
        subjects_list.html("");

        url="dialog/data?"
        url+="samples="+(!disable_sample?"true":"false");
        url+="&variables="+(!disable_variables?"true":"false");
        url+="&subjects="+(!disable_subject?"true":"false");

        d3.json(url, function(error,data) {
            if (error){
                alert("Couldn't connect to server, please verify if it is running.");
                return;
            }

            var var_data = data["variables"];
            var samples_data = data["samples"];
            var subjects_data = data["subjects"];

            //------ variables -------

            if(!disable_variables)
            {
                var variables = vars_list.selectAll("div.checkbox").data(var_data);

                var input_type;
                if (!multiple_variables){
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
                                if ((!multiple_variables && variables_indices == d.index)
                                    || (multiple_variables && (variables_indices.indexOf(d.index)>=0) )){
                                    return "checked";
                                }
                              return null;
                            });
                        label.append("p").text(function(d){return d.var_name});
                    });
            }


            if(!disable_category){
                var categories = cats_list.selectAll("div.radio").data(var_data.filter(function(e){return e.is_real == 0;}));
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
            }
            //------ samples -------

            if(!disable_sample){
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
            }

            //------ subjects -------

            if(!disable_subject){
                var subject_items =subjects_list.selectAll("div.checkbox").data(subjects_data);

                subject_items.enter().append("div").attr("class","radio")
                    .append("label")
                    .call(function(label){
                        label.append("input").attr("type","radio").attr("name","subject")
                            .attr("value",function(d){return d;})
                            .attr("checked",function(d){
                              if(d==subject_index) return "checked";
                              return null;
                            });
                        label.append("p").text(function(d){
                            return d;
                        });
                    });
                }
    });
    }


    function hide_variable_select_panel(){
    dialog.addClass("hidden");
    button.removeClass("hidden");
    }

    button.click(show_variable_select_panel);
    dialog.find("button.close").click(hide_variable_select_panel);
    dialog.find("#bvz-cancel_variable_selection").click(hide_variable_select_panel);

    function filter_variables_list(list, mask){
    mask=mask.toUpperCase();
    $(list).children("div.variable-list div").addClass("hidden");
    $(list).children("div.variable-list div").filter(function (){
        return this.textContent.toUpperCase().indexOf(mask)>=0 ;})
        .removeClass("hidden");
    }

    $("#bvz-search-vars").bind("input", function(){
                filter_variables_list($("#bvz-variables-list-tab").find("div.variable-list"),
                $("#bvz-search-vars").val());
                });

    $("#bvz-search-cats").bind("input", function(){
                filter_variables_list($("#bvz-category-list-tab").find("div.variable-list"),
                $("#bvz-search-cats").val());
                });

    function clear_list(){
    $("#bvz-variables-list-tab").find("div.variable-list input").prop("checked", false);
    }
    $("#bvz-clear_checked_variables").click(clear_list);

    $('#variable-control-tabs').find('a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
    });


    function apply_new_variables(){

    var checked_boxes = $("#bvz-variables-list-tab").find("div.variable-list").find("input")
        .filter(function(i,e){return e.checked;});
    var new_vars = checked_boxes.map(function(i, e){return e.value}).toArray();
    if (!multiple_variables){
        new_vars = new_vars[0];
    }

    var new_cat_idx = $("#bvz-category-list-tab").find("div.variable-list").find("input")
        .filter(function(i,e){return e.checked;}).val();
    var selected_sample = $("#bvz-samples-list-tab").find("div.samples-list").find("input")
        .filter(function(i,e){return e.checked;}).val();
    var new_subject = $("#bvz-subjects-list-tab").find("div.subjects-list").find("input")
        .filter(function(i,e){return e.checked;}).val();


    apply_callback({
        "variables" : new_vars,
        "category" : new_cat_idx,
        "sample" : selected_sample,
        "subject" : new_subject
        });

        hide_variable_select_panel();
    }


    $("#bvz-apply-variable-change").click(apply_new_variables);


}
//---------------------EXPORT-------------------------------------

var braviz_module = {};
braviz_module.connect_to_ws = connect_to_ws;
braviz_module.configure_variables_and_samples_dialog = configure_variables_and_samples_dialog;
return braviz_module;
})();