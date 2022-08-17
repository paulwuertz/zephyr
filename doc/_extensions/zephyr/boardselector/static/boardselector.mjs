/*
 * Copyright (c) Paul Würtz
 * SPDX-License-Identifier: Apache-2.0
 */

const DB_FILE = 'board/board.json';
const MAX_RESULTS = 10;

/* search state */
let db;
let searchOffset;

/* elements */
let input;
let summaryText;
let results;
let navigation;
let navigationPagesText;
let navigationPrev;
let navigationNext;

/**
 * Show an error message.
 * @param {String} message Error message.
 */
function showError(message) {
    const admonition = document.createElement('div');
    admonition.className = 'admonition error';
    results.replaceChildren(admonition);

    const admonitionTitle = document.createElement('p');
    admonitionTitle.className = 'admonition-title';
    admonition.appendChild(admonitionTitle);

    const admonitionTitleText = document.createTextNode('Error');
    admonitionTitle.appendChild(admonitionTitleText);

    const admonitionContent = document.createElement('p');
    admonition.appendChild(admonitionContent);

    const admonitionContentText = document.createTextNode(message);
    admonitionContent.appendChild(admonitionContentText);
}

/**
 * Show a progress message.
 * @param {String} message Progress message.
 */
function showProgress(message) {
    const p = document.createElement('p');
    p.className = 'centered';
    results.replaceChildren(p);

    const pText = document.createTextNode(message);
    p.appendChild(pText);
}

/**
 * Render a Kconfig literal property.
 * @param {Element} parent Parent element.
 * @param {String} title Title.
 * @param {String} content Content.
 */
function renderBoardPeripheral(parent, title, content) {
    const term = document.createElement('dt');
    parent.appendChild(term);

    const termText = document.createTextNode(title);
    term.appendChild(termText);

    const details = document.createElement('dd');
    parent.appendChild(details);

    const literal = document.createElement('span');
    details.appendChild(literal);

    const literalText = document.createTextNode(content);
    literal.appendChild(literalText);
}

/**
 * Render a board entry.
 * @param {Object} entry board entry.
 */
function renderBoardEntry(entry) {
    const container = document.createElement('dl');
    container.className = 'kconfig';

    /* title (name and permalink) */
    const title = document.createElement('dt');
    title.className = 'sig sig-object';
    container.appendChild(title);

    const name = document.createElement('span');
    name.className = 'pre';
    title.appendChild(name);

    const nameText = document.createTextNode(entry.name);
    name.appendChild(nameText);

    // const permalink = document.createElement('a');
    // permalink.className = 'headerlink';
    // permalink.href = '#' + entry.name;
    // title.appendChild(permalink);

    // const permalinkText = document.createTextNode('\uf0c1');
    // permalink.appendChild(permalinkText);

    /* details */
    const details = document.createElement('dd');
    container.append(details);

    /* prompt and help */
    const prompt = document.createElement('p');
    details.appendChild(prompt);
    prompt.innerHTML = "Peripherals:";

    // if (entry.help) {
    //     const help = document.createElement('p');
    //     details.appendChild(help);

    //     const helpText = document.createTextNode(entry.help);
    //     help.appendChild(helpText);
    // }

    /* symbol properties (defaults, selects, etc.) */
    const props = document.createElement('dl');
    props.className = 'field-list simple';
    details.appendChild(props);

    renderBoardPeripheral(props, 'gpio', entry.gpio.count);
    renderBoardPeripheral(props, 'i2c', entry.i2c.count);
    renderBoardPeripheral(props, 'spi', entry.spi.count);
    renderBoardPeripheral(props, 'uart', entry.uart.count);
    renderBoardPeripheral(props, 'can', entry.can.count);
    renderBoardPeripheral(props, 'serial', entry.serial.count);
    renderBoardPeripheral(props, 'quadspi', entry.quadspi.count);
    renderBoardPeripheral(props, 'usart', entry.usart.count);
    renderBoardPeripheral(props, 'adc', entry.adc.count);
    renderBoardPeripheral(props, 'dac', entry.dac.count);
    renderBoardPeripheral(props, 'pwm', entry.pwm.count);
    renderBoardPeripheral(props, 'usb', entry.usb.count);
    renderBoardPeripheral(props, 'ethernet', entry.ethernet.count);

    return container;
}

/** Perform a search and display the results. */
function doSearch() {
    /* replace current state (to handle back button) */
    // history.replaceState({
    //     value: input.value,
    //     searchOffset: searchOffset
    // }, '', window.location);

    // /* nothing to search for */
    // if (!input.value) {
    //     summaryText.nodeValue = '';
    //     results.replaceChildren();
    //     navigation.style.visibility = 'hidden';
    //     return;
    // }

    // /* perform search */
    // let pattern = new RegExp(input.value, 'i');
    let count = 0;

    const searchResults = db.filter(entry => {
        if (entry.name) {
            count++;
            return true;
        } else
            return false;
    });

    /* show results count */
    summaryText.nodeValue = `${count} options match your search.`;

    /* update navigation */
    navigation.style.visibility = 'visible';
    // navigationPrev.disabled = searchOffset - MAX_RESULTS < 0;
    // navigationNext.disabled = searchOffset + MAX_RESULTS > count;

    // const currentPage = Math.floor(searchOffset / MAX_RESULTS) + 1;
    // const totalPages = Math.floor(count / MAX_RESULTS) + 1;
    // navigationPagesText.nodeValue = `Page ${currentPage} of ${totalPages}`;

    /* render Kconfig entries */
    results.replaceChildren();
    searchResults.forEach(entry => {
        results.appendChild(renderBoardEntry(entry));
    });
}

/** Do a search from URL hash */
function doSearchFromURL() {
    const rawOption = window.location.hash.substring(1);
    if (!rawOption) {
        return;
    }

    const option = rawOption.replace(/[^A-Za-z0-9_]+/g, '');
    input.value = '^' + option + '$';

    searchOffset = 0;
    doSearch();
}

function setupBoardSearch() {
    const container = document.getElementById('__board-search-results');
    if (!container) {
        console.error("Couldn't find Kconfig search container");
        return;
    }
    /* populate kconfig-search container - create input field TODO input fields for peripherals here or from json and not in python? */
    // input = document.createElement('input');
    // input.placeholder = 'Type a Kconfig option name (RegEx allowed)';
    // input.type = 'text';
    // container.appendChild(input);
        /* populate kconfig-search container */

    /* create search summary */
    const searchSummary = document.createElement('p');
    searchSummary.className = 'search-summary';
    container.appendChild(searchSummary);

    summaryText = document.createTextNode('');
    searchSummary.appendChild(summaryText);

    /* create search results container */
    results = document.createElement('div');
    container.appendChild(results);

    /* create search navigation */
    navigation = document.createElement('div');
    navigation.className = 'search-nav';
    navigation.style.visibility = 'hidden';
    container.appendChild(navigation);

    navigationPrev = document.createElement('button');
    navigationPrev.className = 'btn';
    navigationPrev.disabled = true;
    navigationPrev.onclick = () => {
        searchOffset -= MAX_RESULTS;
        doSearch();
        window.scroll(0, 0);
    }
    navigation.appendChild(navigationPrev);

    const navigationPrevText = document.createTextNode('Previous');
    navigationPrev.appendChild(navigationPrevText);

    const navigationPages = document.createElement('p');
    navigation.appendChild(navigationPages);

    navigationPagesText = document.createTextNode('');
    navigationPages.appendChild(navigationPagesText);

    navigationNext = document.createElement('button');
    navigationNext.className = 'btn';
    navigationNext.disabled = true;
    navigationNext.onclick = () => {
        searchOffset += MAX_RESULTS;
        doSearch();
        window.scroll(0, 0);
    }
    navigation.appendChild(navigationNext);

    const navigationNextText = document.createTextNode('Next');
    navigationNext.appendChild(navigationNextText);

    /* load database */
    showProgress('Loading database...');

    fetch(DB_FILE)
        .then(response => response.json())
        .then(json => {
            db = json;

            results.replaceChildren();
            doSearch();
            /* perform initial search */
            // doSearchFromURL(); TODO

            /* install event listeners */
            // input.addEventListener('keyup', () => {
            //     searchOffset = 0;
            //     doSearch();
            // }); TODO

            /* install hash change listener (for links) */
            // window.addEventListener('hashchange', doSearchFromURL); TODO

            /* handle back/forward navigation */
            // window.addEventListener('popstate', (event) => {
            //     if (!event.state) {
            //         return;
            //     }

            //     input.value = event.state.value;
            //     searchOffset = event.state.searchOffset;
            //     doSearch();
            // }); TODO
        })
        .catch(error => {
            showError(`Kconfig database could not be loaded (${error})`);
        });
}

var checkbox_select = function(params)
{
    // Error handling first
    // ----------------------------------------------------------------------------------------------------
    var error = false;
    console.log(params.selector);
    // If the selector is not given
    if(!params.selector) {                                              console.error("selector needs to be defined"); error = true; }
    // If the selector is not a string
    if(typeof params.selector != "string") {                            console.error("selector needs to be a string"); error = true; }
    // If the element is not a form
    if(!$(params.selector).is("form")) {                                console.error("Element needs to be a form"); error = true; }
    // If the element doesn't contain a select
    if($(params.selector).find("select").length < 1) {                  console.error("Element needs to have a select in it"); error = true; }
    // If the element doesn't contain option elements
    if($(params.selector).find("option").length < 1) {                  console.error("Select element needs to have an option in it"); error = true; }
    // If the select element doesn't have a name attribute
    if($(params.selector).find('select').attr('name') == undefined) {   console.error("Select element needs to have a name attribute"); error = true; }

    // If there was an error at all, dont continue in the code.
    if(error)
        return false;

    // ----------------------------------------------------------------------------------------------------

    var that            = this,
        $_native_form   = $(params.selector),
        $_native_select = $_native_form.find('select'),

        // Variables
        selector                = params.selector,
        select_name             = $_native_select.attr('name').charAt(0).toUpperCase() + $_native_select.attr('name').substr(1),
        selected_translation    = params.selected_translation   ? params.selected_translation   : "selected",
        all_translation         = params.all_translation        ? params.all_translation        : "All " + select_name + "s",
        not_found_text          = params.not_found              ? params.not_found              : "No " + select_name + "s found.",
        currently_selected      = [],
        conjunctor              = params.conjunctor             ? params.conjunctor             : " or",

        // Create the elements needed for the checkbox select
        $_parent_div    = $("<div />")      .addClass("checkbox_select"),
        $_select_anchor = $("<a />")        .addClass("checkbox_select_anchor")     .text( select_name ),
        $_search        = $("<input />")    .addClass("checkbox_select_search"),
        $_submit        = $("<input />")    .addClass("checkbox_select_submit")     .val("Apply") .attr('type','submit') .data("selected", ""),
        $_dropdown_div  = $("<div />")      .addClass("checkbox_select_dropdown"),
        $_not_found     = $("<span />")     .addClass("not_found hide")             .text(not_found_text),
        $_ul            = $("<ul />"),

        updateCurrentlySelected = function(){
            var selected = [], selected_display_string = "";

            $_ul.find("input:checked").each(

                function(){
                    selected.push($(this).val());
                    selected_display_string += $(this).val().toLocaleUpperCase() + ", "
                }
            );
            selected_display_string = selected_display_string.substring(0, selected_display_string.length - 2)
            let last_comma = selected_display_string.lastIndexOf(",")
            if (last_comma != -1) {
                let before_last_comma = selected_display_string.substring(0, last_comma)
                let after_last_comma = selected_display_string.substring(last_comma + 1)
                selected_display_string = before_last_comma + conjunctor + after_last_comma
            }

            currently_selected = selected;

            if(selected.length == 0){
                $_select_anchor.text( select_name )
            }
            else if(selected.length == 1){
                $_select_anchor.text( selected_display_string + " " + select_name );
            }
            else{
                $_select_anchor.text( selected_display_string + " " + select_name + "s" );
            }
        },

        // Template for the li, will be used in a loop.
        createItem  = function(name, value){
            var uID             = 'checkbox_select_' + select_name + "_" + name.replace(" ", "_"),
                $_li            = $("<li />"),
                $_checkbox      = $("<input />").attr({
                                            'name'  : name,
                                            'id'    : uID,
                                            'type'  : "checkbox",
                                            'value' : value
                                        }
                                    )
                                    .click(

                                        function(){
                                            updateCurrentlySelected();
                                        }
                                    ),

                $_label         = $("<label />").attr('for', uID),
                $_name_span     = $("<span />").text(name).prependTo($_label);
                $_li.append( $_checkbox )
                $_li.append( $_label )
            return $_li;
        },

		apply = function(){
			$_dropdown_div.toggleClass("show");
			$_parent_div.toggleClass("expanded");

			if(!$_parent_div.hasClass("expanded")){
				// Only do the Apply event if its different
				if(currently_selected != $_submit.data("selected")){
					$_submit.data("selected" , currently_selected);

					that.onApply({
                        selected : $_submit.data("selected")
                    });
				}
			}
		};

    // Event of this instance
    that.onApply = typeof params.onApply == "function" ?

                    params.onApply :

                    function(e){
                        //e.selected is accessible
                    };

    that.update = function(){
        $_ul.empty();
        $_native_select.find("option").each(function(i){
            $_ul.append( createItem( $(this).text(), $(this).val() ) );
        });
        updateCurrentlySelected();
    }

    that.check = function(checkbox_name, checked){
        //$_ul.find("input[type=checkbox][name=" + trim(checkbox_name) + "]").attr('checked', checked ? checked : false);

		$_ul.find("input[type=checkbox]").each(function(){
			// If this elements name is equal to the one sent in the function
			if($(this).attr('name') == checkbox_name){
				// Apply the checked state to this checkbox
				$(this).attr('checked', checked ? checked : false);

				// Break out of each loop
				return false;
			}
		});

        updateCurrentlySelected();

    }

    // Build mark up before pushing into page
    $_dropdown_div  .prepend($_search);
    $_dropdown_div  .append($_ul);
    $_dropdown_div  .append($_not_found);
    $_dropdown_div  .append($_submit);
    $_dropdown_div  .appendTo($_parent_div);
    $_select_anchor .prependTo($_parent_div);

    // Iterate through option elements
    that.update();

    // Events

    // Actual dropdown action
    $_select_anchor.click(

        function(){
            apply();
        }
    );

    // Filters the checkboxes by search on keyup
    $_search.keyup(

        function(){
            var search = $(this).val().toLowerCase().trim();

            if( search.length == 1 ){
                $_ul.find("label").each(

                    function(){
                        if($(this).text().toLowerCase().charAt(0) == search.charAt(0)){
                            if($(this).parent().hasClass("hide"))
                                $(this).parent().removeClass("hide");

                            if(!$_not_found.hasClass("hide"))
                                $_not_found.addClass("hide");
                        }
                        else{
                            if(!$(this).parent().hasClass("hide"))
                                $(this).parent().addClass("hide");

                            if($_not_found.hasClass("hide"))
                                $_not_found.removeClass("hide");
                        }
                    }
                );
            }
            else{
                // If it doesn't contain
                if($_ul.text().toLowerCase().indexOf(search) == -1){
                    if($_not_found.hasClass("hide"))
                        $_not_found.removeClass("hide");
                }
                else{
                    if(!$_not_found.hasClass("hide"))
                        $_not_found.addClass("hide");
                }

                $_ul.find("label").each(

                    function(){
                        if($(this).text().toLowerCase().indexOf(search) > -1){
                            if($(this).parent().hasClass("hide"))
                                $(this).parent().removeClass("hide");
                        }
                        else{
                            if(!$(this).parent().hasClass("hide"))
                                $(this).parent().addClass("hide");
                        }
                    }
                );
            }
        }
    );

    $_submit.click(
        function(e){
            e.preventDefault();
            apply();
        }
    );

    // Delete the original form submit
    $(params.selector).find('input[type=submit]').remove();

    // Put finalized markup into page.
    $_native_select.after($_parent_div);

    // Hide the original element
    $_native_select.hide();
};

$( document ).ready(function() {
    console.log( "ready!" );
    // init filter chips
    for (let selectCheckbox of $(".filter-form")) {
        if(selectCheckbox.id) {
            new checkbox_select({
                selector : "#"+selectCheckbox.id,
                selected_translation : "Filters choosen",
                all_translation : "All filters active",
                not_found : "No boards matched your filters...",

                // Event during initialization
                onApply : function(e)
                {
                    alert("Custom Event: " + e.selected);
                }
            });
        }
    }
    // init filter selector
    new checkbox_select({
        selector : "#filter-filter-checkboxes",
        selected_translation : "Filters choosen",
        all_translation : "All filters active",
        not_found : "No boards matched your filters...",
        conjunctor: " and",

        // Event during initialization
        onApply : function(e)
        {
            alert("Custom Event: " + e.selected);
        }
    });

    setupBoardSearch();
});

//setupKconfigSearch();
