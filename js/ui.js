/*jslint maxerr: 50, indent: 4 */
/*globals $,document,console*/
if (typeof formdesigner === 'undefined') {
    var formdesigner = {};
}

formdesigner.ui = (function () {
    "use strict";
    var that = {}, question_list = [],
    buttons = {},
    controller = formdesigner.controller,
    questionTree;

    var appendErrorMessage = that.appendErrorMessage = function (msg) {
        $('#fd-notify').addClass("notice");
        $('#fd-notify').text($('#fd-notify').text() + msg);
    };

    function do_loading_bar() {
        var pbar = $("#progressbar"),
        content = $("#content"),
        loadingBar = $("#loadingBar"),
                doneController = false,
                doneUtil = false,
                doneModel = false,
                doneTree = true,
                allDone = false,
                tryComplete = function () {
                    allDone = doneUtil && doneController && doneModel;
                    if (allDone) {
                        loadingBar.delay(500).fadeOut(500);
                    }
                };

        content.show();
        loadingBar.css("background-color", "white");
        loadingBar.fadeIn(100);

        pbar.progressbar({ value: 0 });

//        $("#loadingInfo").html("downloading jstree.js");
//        $.getScript("js/jquery.jstree.js", function () {
//            pbar.progressbar({ value: (pbar.progressbar( "option", "value" )+25)});
//            doneTree = true;
//            tryComplete();
//        });
//
//        $("#loadingInfo").html("downloading util.js");
//        $.getScript("js/util.js", function () {
//            pbar.progressbar({ value: (pbar.progressbar( "option", "value" )+25)});
//            doneUtil = true;
//            tryComplete();
//        });
//
//        $("#loadingInfo").html("downloading model.js");
//        $.getScript("js/model.js", function () {
//            pbar.progressbar({ value: (pbar.progressbar( "option", "value" )+25)});
//            doneModel = true;
//            tryComplete();
//        });
//
//        $("#loadingInfo").html("downloading controller.js");
//        $.getScript("js/controller.js", function () {
//            pbar.progressbar({ value: (pbar.progressbar( "option", "value" )+25)});
//            doneController = true;
//            tryComplete();
//        });
//
//        window.setTimeout(function () {
//            if (!allDone) {
//                    allDone = doneUtil && doneController && doneModel && doneTree;
//                    if (allDone) {
//                        loadingBar.delay(500).fadeOut(500);
//                    }else{
//                        var alertString = '';
//                        if (!doneUtil) { alertString += '[Util.js]'; }
//                        if (!doneController) { alertString += '[Controller.js]';}
//                        if (!doneModel) { alertString += '[Model.js]';}
//                        if (!doneTree) { alertString += '[jsTree]'; }
//
//                        alert("Problem loading FormDesigner Libraries! Libraries not loaded: "+alertString);
//                    }
//            }
//                }, 5000);

        loadingBar.fadeOut(200);

    }

    function init_toolbar() {
        var toolbar = $(".fd-toolbar");
        var buts =  $(".questionButton");

        //make each element a button
        buts.button();

        //bind a function to the click event for each button
        buts.each(function (index) {
           var qType = $(this).attr("id").split('-')[2],
                   name = $(this).attr("id").replace('fd-','').replace('-','').replace('-','');
           $(this).click(function (){
              formdesigner.controller.createQuestion(qType);
           });
           buttons[name] = $(this);
        });

        //debug tools
        (function c_printDataTreeToConsole() {
            var printTreeBut = $(
                    '<div id="fd-print-tree-button">'+
                '<span id="fd-print-tree-but"></span>Print DATA tree to Console ' +
              '</div>');
            toolbar.append(printTreeBut);

            printTreeBut.button().click(function () {
                console.group("Tree Pretty Print");
                console.log("Control Tree:"+controller.form.controlTree.printTree())
                console.log("Data Tree:   "+controller.form.dataTree.printTree());
                console.groupEnd();
            });
            $("#fd-print-tree-but")
                    .addClass("ui-corner-all ui-icon ui-icon-plusthick")
                    .css("float", "left");

            buttons.printTree = printTreeBut;
        })();

       (function c_fancyBox() {
            var fancyBut = $(
                    '<div id="fd-fancy-button">'+
                '<span id="fd-fancy-but"></span>View Source ' +
              '</div>');
            toolbar.append(fancyBut);

            fancyBut.button().click(function () {
                var d = controller.get_form_data();
                var output = $('#data');
                output.text(d);
                $('#inline').click();
            });
            $("#fd-print-tree-but")
                    .addClass("ui-corner-all ui-icon ui-icon-plusthick")
                    .css("float", "left");

            buttons.fancyBut = fancyBut;
        })();



    }
    that.buttons = buttons;

    function getJSTreeTypes() {
        var groupRepeatValidChildren = formdesigner.util.GROUP_OR_REPEAT_VALID_CHILDREN,
        types =  {
            "max_children" : -1,
			"valid_children" : groupRepeatValidChildren,
			"types" : {
                "group" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-16px -96px"
                    },
                    "valid_children" : groupRepeatValidChildren
                },
                "repeat" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-64px -80px"
                    },
                    "valid_children" : groupRepeatValidChildren
                },
                "question" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-128px -96px"
                    },
                    "valid_children" : "none"
                },
                "selectQuestion" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-96px -176px"
                    },
                    "valid_children": ["item"]
                },
                "item" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-48px -128px"
                    },
                    "valid_children" : "none"
                },
                "trigger" : {
                    "icon": {
                        "image" : "css/smoothness/images/ui-icons_888888_256x240.png",
                        "position": "-16px -144px"
                    },
                    "valid_children" : "none"
                },
				"default" : {
					"valid_children" : groupRepeatValidChildren
				}
			}
		};
        return types;

    }

    that.displayMugProperties = that.displayQuestion = function(mugType){
        if (!mugType.properties.controlElement) {
            //fuggedaboudit
            throw "Attempted to display properties for a MugType that doesn't have a controlElement!";
        }


        var displayFuncs = {};

        /**
         * Runs through a properties block and generates the
         * correct li elements (and appends them to the given parentUL)
         *
         * @param propertiesBlock
         * @param parentUL
         */
        function listDisplay(propertiesBlock,parentUL, mugProps){
            var i, li;
            for(i in propertiesBlock){
                if(propertiesBlock.hasOwnProperty(i) && propertiesBlock[i].visibility === 'visible'){
                    var pBlock = propertiesBlock[i],
                            labelStr = pBlock.lstring ? pBlock.lstring : i,
                            liStr = '<li>'+labelStr+': '+'<input>'+'</li>';
                    li = $(liStr);
                    parentUL.append(li);
                }
            }
        }

        function showControlProps(){
            var properties = mugType.properties.controlElement,
                    uiBlock = $('#fd-props-control'),
                    ul;

            uiBlock.empty(); //clear it out first in case there's anything present.
            ul = $('<ul>Control Props</ul>');


            listDisplay(properties,ul,mugType.mug.properties.controlElement.properties);
            uiBlock.append(ul);
            uiBlock.show();
        }
        displayFuncs.controlElement = showControlProps;

        function showDataProps(){
            var properties = mugType.properties.dataElement,
                    uiBlock = $('#fd-props-data'),
                    ul;
            uiBlock.empty(); //clear it out first in case there's anything present.
            ul = $('<ul>Data Props</ul>');

            listDisplay(properties,ul,mugType.mug.properties.dataElement);
            uiBlock.append(ul);
            uiBlock.show();
        }
        displayFuncs.dataElement = showDataProps;


        function showBindProps(){
            var properties = mugType.properties.bindElement,
                    uiBlock = $('#fd-props-bind'),
                    ul;
            uiBlock.empty(); //clear it out first in case there's anything present.
            ul = $('<ul>Bind Props</ul>');


            listDisplay(properties,ul,mugType.mug.properties.bindElement.properties);
            uiBlock.append(ul);
            uiBlock.show();
        }
        displayFuncs.bindElement = showBindProps;

        function showItextProps(){

        }
        displayFuncs.itext = showItextProps; //not sure if this will ever be used like this, but may as well stick with the pattern

        function updateDisplay(){
            var mugTProps = mugType.properties,
            i = 0;
            $('#fd-props-bind').empty();
            $('#fd-props-data').empty();
            $('#fd-props-control').empty();
            for(i in mugTProps){
                if(mugTProps.hasOwnProperty(i)){
                    displayFuncs[i]();
                }
            }
        };

        updateDisplay();
    }



    /**
     * Updates the properties view such that it reflects the
     * properties of the currently selected tree item.
     *
     * This means it will show only fields that are available for this
     * specific MugType and whatever properties are already set.
     *
     *
     * @param mugType
     */
    that.displayMugProperties2 = function (mugType) {
        var that = {},
                qTable,
                qTHeader,
                qTBody,
                localMug = mugType.mug,
                qPropHolder,
                showPropertiesFactory = {};

        if (!mugType.properties.controlElement) {
            //fuggedaboudit
            throw "Attempted to display properties for a MugType that doesn't have a controlElement!";
        }

        qPropHolder = $('#fd-question-properties');
        qPropHolder.empty();
        that.qTable = qTable;
        that.qTHeader = qTHeader;
        that.qTBody = qTBody;




        /**
         * Creates the Properties Box on the UI
         */
        var create = function (mugT, title) {
            var i,
            mug = mugT.mug,
            mugTProps = mugT.properties,
            mugProps = mug.properties;


            qTable = $('<table id="fd-question-table" class=fd-"'+title+'"></table>');
            qPropHolder.append(qTable);
            qTHeader = $('<thead class="fd-question-table-header"></thead>');
            qTHeader.append('<tr><td colspan = 2><b><h1>Question Properties: '+controller.getTreeLabel(mugT)+'</h1></b></td></tr>');
            qTHeader.append("<tr><td><b>Property Name</b></td><td><b>Property Value</b></td></tr>");
            qTable.append(qTHeader);
            qTBody = $("<tbody></tbody>");
            qTable.append(qTBody);


            i = 'ufid';
            var row, col1, col2;

            row = $("<tr></tr>");
            qTBody.append(row);
            row.attr('id', 'fd-'+i);
            row.attr('class', "fd-question-property-row");
            col1 = $("<td></td>");
            col2 = $("<td></td>");
            row.append(col1);
            row.append(col2);

            col1.html(i);
            col2.html(mug[i]);
            for(var p in mugProps) {
                var block = mugProps[p].properties;
                if (!mugProps.hasOwnProperty(p)) {
                    continue;
                }
                if (typeof block === 'function' || typeof block === 'string') {
                    continue;
                }

                qTBody.append("<hr />");
                qTBody.append('<tr><td colspan = 2><h2 class="fd-properties-block-header">'+p+' Properties:</h2></tr>')

                for(i in block) {
                    var inputBox;
                    if (!block.hasOwnProperty(i) || typeof block[i] === 'function') {
                        continue;
                    }
                    row = $("<tr></tr>");
                    qTBody.append(row);
                    row.attr('id', 'fd-'+i);
                    row.attr('class', "fd-question-property-row");
                    col1 = $('<td class="fd-prop-title title">'+i+'</td>');
                    col2 = $('<td class="fd-value"></td>');
                    inputBox = $('<input value="'+block[i]+'" name="fd-'+i+'" class="fd-'+p+' fd-edit title" />');
                    col2.append(inputBox);
                    inputBox.change(function (e) {
                        var target = $(e.target),
                                el = target.attr("class").replace('fd-',''),
                                prop = target.attr("name").replace('fd-',''),
                                newVal = target.val().replace('"','').replace('"','');
                        setPropertyValForModel(mug, el, prop, newVal);
                    });
                    row.append(col1);
                    row.append(col2);
                }
            }

            $('input[class="fd-dataElement"][name="fd-nodeID"]').keyup(function () {
                var node = $('#'+controller.getCurrentlySelectedMug().ufid);
                $('#fd-question-tree').jstree("rename_node",node, this.value);
            })




        }(mugType, localMug.ufid);

        /**
         * Used for setting up the basic skeleton for properties editing
         * (i.e. all the stuff that's common across the different MugTypes)
         * @param mugT
         * @return an object containing the various fields/items that are
         * usefully editable
         */
        showPropertiesFactory.generic = function (mugT) {

        }



        /**
         * Shows the properties that are editable by the user
         * (as either a repeat or group)
         * @param mugT - the MugType associated with this group/repeat
         * @param isRepeat
         */
        showPropertiesFactory.group = showPropertiesFactory.repeat = function (mugT) {
            var fields = showPropertiesFactory.generic(mugT);
        }

        /**
         * Here 'Normal Question' means whatever
         * isn't a repeat, group, (1)select, item, trigger
         * @param mugT
         */
        var showNormalQuestionProperties = function (mugT) {
            var fields = showPropertiesFactory.generic(mugT);
        }
        var s = showPropertiesFactory;
        s.text = s.int = s.long = s.double = s.date = s.datetime = s.picture = showNormalQuestionProperties;

        //We use the showProperties object as dictionary to make it easier to select
        //the right function based on the MugType without a pita long and complex if/switch statement.

        /**
         * Shows the props for 1selec/select type questions
         * @param mugT
         */
        var showSelectQuestionProperties = function (mugT) {
            var fields = showPropertiesFactory.generic(mugT);
        }

        /**
         * Shows props for Items (in a select/1select).
         * @param itemData - the data object associated with this item
         */
        var showSelectItemProperties = function (itemData) {

        }

        /**
         * Shows the props for a Trigger item.
         * @param mugT
         */
        var showTriggerProperties = function (mugT) {

        }


        function setPropertyValForUI(property, value) {
            $(".fd-question-property-row fd-"+property+" td:nth-child(2)").html(value);
        }
        that.setPropertValForUI = setPropertyValForUI;

        /**
         *
         * @param element can be one of (string) 'bind','data','control'
         * @param property (string) property name
         * @param val new value the property should be set to.
         */
        function setPropertyValForModel(myMug, element, property, val) {
            var rootProps = myMug['properties'];
            var elProps = rootProps[element].properties,
                propertyToChange = elProps[property], event = {};

            myMug.properties[element].properties[property] = val;
            event.type = 'property-changed';
            event.property = property;
            event.element = element;
            event.val = val;
            myMug.fire(event);

        }

        return that;
    };

    /**
     * Private function (to the UI anyway) for handling node_select events.
     * @param e
     * @param data
     */
    function node_select(e, data) {
        var curSelUfid = jQuery.data(data.rslt.obj[0], 'mugTypeUfid');
        formdesigner.controller.setCurrentlySelectedMugType(curSelUfid);
        that.displayMugProperties(formdesigner.controller.getCurrentlySelectedMugType());
    }
    
    /**
     * Creates the UI tree
     */
    function create_question_tree() {
        $.jstree._themes = "themes/";
        $("#fd-question-tree").jstree({
            "json_data" : {
                "data" : []
            },
            "crrm" : {
                "move": {
                    "always_copy": false,
                    "check_move" : function (m) {
                        var controller = formdesigner.controller,
                                mugType = controller.form.controlTree.getMugTypeFromUFID($(m.o).attr('id')),
                                refMugType = controller.form.controlTree.getMugTypeFromUFID($(m.r).attr('id')),
                                position = m.p;
                        return controller.checkMoveOp(mugType, position, refMugType);
				    }
                }
            },
            "dnd" : {
                "drop_target" : false,
                "drag_target" : false
            },
            "types": getJSTreeTypes(),
            "plugins" : [ "themes", "json_data", "ui", "types", "crrm", "dnd" ]
	    }).bind("select_node.jstree", function (e, data) {
                    node_select(e, data);
        }).bind("move_node.jstree", function (e, data) {
                    var controller = formdesigner.controller,
                                mugType = controller.form.controlTree.getMugTypeFromUFID($(data.rslt.o).attr('id')),
                                refMugType = controller.form.controlTree.getMugTypeFromUFID($(data.rslt.r).attr('id')),
                                position = data.rslt.p;
                    controller.moveMugType(mugType, position, refMugType);
                });
        questionTree = $("#fd-question-tree");
    }

    /**
     *
     * @param rootElement
     */
    var generate_scaffolding = function (rootElement) {
        var root = $(rootElement);
        $.ajax({
            url: 'templates/main.html',
            async: false,
            cache: false,
            success: function(html){
                root.append(html);
                console.log("Successfully loaded main template!");
            }
        });

    };

    var init_extra_tools = function(){
        var eContainer = $("fd-extra-tools"),
            accordion = $("#fd-extra-tools-accordion"),
                min_max = $('#fd-acc-min-max');
        accordion.accordion({
            fillSpace: 'true'
        });

        min_max.button();
        min_max.click(function(){
            var b = $("#fd-extra-tools"),
            curRight = b.css('right');
            if(curRight === '-255px'){
                b.animate({
                    right:'0px'
                },200);
            }else if(curRight === "0px"){
                b.animate({
                    right:'-255px'
                },200);
            }
        });
        
    };

    var create_data_tree = function(){
        var tree = $("#fd-data-tree-container");
        tree.hover(
                function () {
                    $(this).stop().animate({
                        'left': '0px'
                    }, 200);
                },
                function () {
                    $(this).stop().animate({
                        'left': '-260px'
                    }, 200);
                }
            );

        //DATA TREE
        tree = $("#fd-data-tree");
        tree.jstree({
            "json_data" : {
                "data" : []
            },
            "crrm" : {
                "move": {
                    "always_copy": false,
                    "check_move" : function (m) {
                        var controller = formdesigner.controller,
                                mugType = controller.form.controlTree.getMugTypeFromUFID($(m.o).attr('id')),
                                refMugType = controller.form.controlTree.getMugTypeFromUFID($(m.r).attr('id')),
                                position = m.p;
                        return controller.checkMoveOp(mugType, position, refMugType);
				    }
                }
            },
//            "dnd" : {
//                "drop_target" : false,
//                "drag_target" : false
//            },
            "types": getJSTreeTypes(),
            "plugins" : [ "themes", "json_data", "ui", "types", "crrm" ]
	    }).bind("select_node.jstree", function (e, data) {
//                    node_select(e, data);
        }).bind("move_node.jstree", function (e, data) {
//                    var controller = formdesigner.controller,
//                                mugType = controller.form.controlTree.getMugTypeFromUFID($(data.rslt.o).attr('id')),
//                                refMugType = controller.form.controlTree.getMugTypeFromUFID($(data.rslt.r).attr('id')),
//                                position = data.rslt.p;
//                    controller.moveMugType(mugType, position, refMugType);
        });


    };

    function setup_fancybox(){
        $("a#inline").fancybox({
            hideOnOverlayClick: false,
            hideOnContentClick: false,
            enableEscapeButton: false,
            showCloseButton : true,
            onClosed: function(){
    //                console.log("onClosed called");
            }
        });

        $('#fancybox-overlay').click(function () {
//            console.log('overlay clicked!');
        })
    };

    $(document).ready(function () {
        generate_scaffolding($("#formdesigner"));
        do_loading_bar();
        init_toolbar();
        init_extra_tools();
        create_question_tree();
        create_data_tree();

        controller = formdesigner.controller;
        controller.initFormDesigner();

        setup_fancybox();


    });

    return that;
}());

