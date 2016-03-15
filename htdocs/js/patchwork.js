var pw = (function() {
    'use strict';

    /* ES 6 */
    function setup_polyfill_endswith() {
        if (String.prototype.endsWith)
            return;

        String.prototype.endsWith = function(searchString, position) {
            var subjectString = this.toString();
            if (typeof position !== 'number' || !isFinite(position) ||
                Math.floor(position) !== position ||
                position > subjectString.length) {
                position = subjectString.length;
            }
            position -= searchString.length;
            var lastIndex = subjectString.indexOf(searchString, position);
            return lastIndex !== -1 && lastIndex === position;
        };
    }

    function setup_polyfill_startswith() {
        if (String.prototype.startsWith)
            return;

        String.prototype.startsWith = function(searchString, position) {
            position = position || 0;
            return this.indexOf(searchString, position) === position;
        };
    }

    function setup_polyfills() {
        setup_polyfill_endswith();
        setup_polyfill_startswith();
    }

    function get_value_from_path(obj, path) {
        var parts = path.split('.');

        for (var i = 0; i < parts.length; i++) {
            obj = obj[parts[i]];
            if (!obj)
                return obj;
        }
        return obj;
    }

    function get_cookie(name) {
        var value = null;

        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = $.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    value = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return value;
    }

    var exports = {},
        ctx = {
            base_url: '',
            api_base_url: '/api/1.0',
            project: null,
            user : {
                is_authenticated: false,
                items_per_page: 100,
            },
            table: null,
        };

    exports.post_data = function(url, data, success_cb, error_cb) {
        $.ajax({
            url: ctx.api_base_url + url,
            headers: {
                'X-HTTP-Method-Override': 'PATCH',
                'X-CSRFToken': get_cookie('csrftoken'),
            },
            type: 'POST',
            data: data,
            success: function(response) {
                if (success_cb) success_cb();
            },
            error: function(ctx, status, error) {
                console.log("Couldn't patch " + " with " + JSON.stringify(data) + ": " + status, error);
                if (error_cb) error_cb();
            }
        });
    };

    function create_table(config) {
        var o = {
            filters: [],
            /* list of object ids to highlight at refresh() */
            _highlight_objects: [],
        };

        $.extend(o, config);

        o._dynatable = function() {
            return $(this.selector).data('dynatable');
        };

        o.url = function() {
            return o.api_url + '?' + $.param(o.api_params);
        };

        o.set_filter = function (param, val) {
            if (val === undefined || val === null || val === '') {
                delete o.api_params[param];
                return;
            }

            o.api_params[param] = val;
        };

        o.refresh = function() {
            var dynatable = this._dynatable();

            dynatable.paginationPage.set(1);
            dynatable.settings.dataset.ajaxUrl = this.url();
            dynatable.process();
        };

        o.add_filter = function(filter) {
            this.filters.push(filter);
        };

        o.set_info = function(content) {
            if (!content) {
                $(this.selector + '-info-container').hide();
                return;
            }

            $(this.selector + '-info-container').fadeIn();
            $(this.selector + '-info').html(content);
        };

        o.count = function() {
            return this._dynatable().settings.dataset.totalRecordCount;
        };

        o._refresh_select_checkboxes = function() {
            if (!this.ctx.project.is_editable) {
                $('#css-table-select').html('.table-select { display: none; }');
                return;
            }

            $('#css-table-select').html('');

            this._for_each_checkbox(function() {
                $(this).click(function() {
                    if ($(this).is(':checked'))
                        o._select_row($(this));
                    else
                        o._deselect_row($(this));
                });
            });

            /* clear the "check all" checkbox */
            $(o.selector + '-select-all').prop('checked', false);
        };

        o.refresh_info = function(content) {
            var descriptions = [];

            for (var i = 0; i < this.filters.length; i++) {
                var filter = this.filters[i];

                if (!filter.is_active)
                    continue;

                descriptions.push(filter.humanize());
            }

            var text, count = this.count();
            if (descriptions.length === 0) {
                text = "Showing all " + count + " " + this.name;
                $(this.selector + '-showall').hide();
            } else {
                text = "Showing " + count + " " + this.name + ' ';
                text += descriptions.join(', ');
                $(this.selector + '-showall').show();
            }
            this.set_info(text);
        };

        o._refresh_highlight = function() {
            this._for_each_checkbox(function() {
                var id = o.id_from_checkbox($(this));
                if (o._highlight_objects.indexOf(id) != -1)
                    $(this).parent().parent().addClass('flash');
            });
            o._highlight_objects = [];
        };

        /* called when dynatable has finished populating the DOM */
        o.on_update_finished = function() {
            this._refresh_select_checkboxes();
            this.refresh_info();
            this._refresh_highlight();
            this._refresh_actions();
        };

        o._for_each_checkbox = function(callback) {
            $(o.selector + ' tbody tr td input:checkbox').each(callback);
        };

        o.id_from_checkbox = function(checkbox) {
            return checkbox.parent().next().html();
        };

        o._refresh_actions = function() {
            var n_selected = 0;

            o._for_each_checkbox(function() {
                if($(this).is(':checked'))
                    n_selected++;
            });

            if (n_selected > 0) {
                $(this.selector + '-filters').hide();
                $(this.selector + '-actions').fadeIn();

            } else {
                $(this.selector + '-actions').hide();
                $(this.selector + '-filters').fadeIn();
            }
        };

        o._row_selection_changed = function() {
           this._refresh_actions();
           $(this.selector).trigger('table-row-selection-changed',
                                    [this, this.table]);
        };

        o._select_row = function(row) {
           row.prop('checked', true);
           row.parent().parent().css('background-color', '#f5f5f5');
           this._row_selection_changed();
        };

        o._deselect_row = function(row) {
           row.prop('checked', false);
           row.parent().parent().css('background-color', 'transparent');
           this._row_selection_changed();
        };

        o._highlight_next_refresh = function(objects) {
            this._highlight_objects = objects;
        };

        o.for_each_selected_row = function(callback) {
            var i = -1;

            this._for_each_checkbox(function() {
                i++;

                if (!$(this).is(':checked'))
                    return;

                callback(o._dynatable().settings.dataset.records[i]);
            });
        };

        /* setup the select-all check box */
        $(o.selector + '-select-all').click(function() {
            if ($(this).is(':checked'))
                o._for_each_checkbox(function() {
                    o._select_row($(this));
                });
            else
                o._for_each_checkbox(function() {
                    o._deselect_row($(this));
                });
        });

        /* 'Show all' link */
        $(o.selector + '-showall').click(function() {
            for (var i = 0; i < o.filters.length; i++) {
                var filter = o.filters[i];

                if (!filter.is_active)
                    continue;

                filter.clear_filter(o);
                filter.set_active(false);
            }
            o.refresh();
        });

        return o;
    }

    var toolbar_mixin = {
        set_radio_disabled: function(radio, disabled) {
            radio.prop('disabled', disabled);
            if (disabled)
                radio.parent().addClass('disabled');
            else
                radio.parent().removeClass('disabled');
        },
    };

    var filter_mixin = {
        set_active: function(val) {
            if (val == this.is_active)
                return;

            this.is_active = val;
            this.refresh_active();
        },

        _clear_filter: function() {
            this.clear_filter(this.table);
            this.table.refresh();
            this.set_active(false);
        },
    };

    /*
     * table: the table the filter applies to
     * name: name of the filter, used to lookup HTML elements
     * init: setup the filter
     * set_filter(table): set the filter(s) on 'table'
     * clear_filter(table): clear the filter(s) on 'table' and reset the
     *                      filter fields
     * can_submit: are the filter fields populated in such a way one can
     *             submit (apply) the filter?
     * humanize: return a string with a description of the active filter for
     *           humans to read
     */
    exports.create_filter = function(config) {
        var o = {};

        $.extend(o, config);
        $.extend(o, filter_mixin);
        $.extend(o, toolbar_mixin);

        o.refresh_apply = function() {
            var submit = $('#' + o.name + '-filter .apply-filter');
            if (this.can_submit())
                submit.removeAttr('disabled').focus();
            else
                submit.attr('disabled', '');
        };

        o.refresh_active = function() {
            if (o.is_active) {
                $('#clear-' + o.name + '-filter, ' +
                  '#' + o.name + '-filter .btn-link').fadeIn();
                $('#' + o.name + '-filter').addClass('filter-applied');
            } else {
                $('#clear-' + o.name + '-filter, ' +
                  '#' + o.name + '-filter .btn-link').fadeOut();
                $('#' + o.name + '-filter').removeClass('filter-applied');

            }
        };

        /* initialize the filter */
        o.init();
        o.clear_filter(o.table);

        $('#' + o.name + '-form').submit(function(e) {
            e.preventDefault();

            o.set_filter(o.table);

            o.table.refresh();
            $('#' + o.name + '-filter-dropdown').dropdown('toggle');

            o.set_active(true);
        });

        $('#clear-' + o.name + '-filter').tooltip();
        $('#clear-' + o.name + '-filter').click(function(e) {
            e.stopPropagation();
            o._clear_filter();
        });
        $('#' + o.name + '-filter .btn-link').click(function(e) {
            e.preventDefault();
            o._clear_filter();
            $('#' + o.name + '-filter-dropdown').dropdown('toggle');
        });

        o.set_active(false);
        o.refresh_apply();

        o.table.add_filter(o);

        return o;
    };

    /* a specialized filter for the search input */
    exports.create_search_filter = function(config) {
        var o = {};

        $.extend(o, config);
        $.extend(o, filter_mixin);

        o.refresh_active = function() {
            if (this.is_active) {
                $('#' + this.name + '-filter .btn-link').fadeIn();
            } else {
                $('#' + this.name + '-filter .btn-link').fadeOut();
            }
        };

        /* install a few call backs */
        $('#' + o.name + '-form').submit(function(e) {
            e.preventDefault();
            if (!o.can_submit())
                return;

            o.set_filter(o.table);
            o.table.refresh();
            o.set_active(true);
        });

        $('#' + o.name + '-filter .btn-default').click(function(e) {
            $('#' + o.name + '-form').submit();
        });

        $('#' + o.name + '-filter .btn-link').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            o._clear_filter();
        });

        /* initialize the filter */
        o.init();
        o.clear_filter(o.table);
        o.set_active(false);
        o.table.add_filter(o);

    };

    /*
     * table: the table the action applies to
     * name: name of the action, used to lookup HTML elements
     * init: setup the action
     * do_action(id): Apply the action on the object with primary key 'id'
     * clear_action: reset the action fields (optional)
     * can_submit: are the fields fields populated in such a way one can
     *             submit (apply) the filter? (optional)
     */
    exports.create_action = function(config) {
        var o = {};

        o._nop = function() {};
        o.can_submit = o._nop;
        o.clear_action = o._nop;
        o._pending_posts = 0;

        $.extend(o, config);
        $.extend(o, toolbar_mixin);

        o.refresh_apply = function() {
            var submit = $('#' + o.name + '-action .apply-action');
            if (submit.length === 0)
                return;
            if (this.can_submit())
                submit.removeAttr('disabled').focus();
            else
                submit.attr('disabled', '');
        };

        o._on_post_complete = function() {
            if (o._pending_posts <= 0) {
                console.log('error: received POST reply with none pending');
                return;
            }

            o._pending_posts--;
            if (o._pending_posts !== 0)
                return;

            o.table.refresh();
        };

        o._on_post_success = function(res) {
            o._on_post_complete();
        };

        o._on_post_failure = function() {
            o._on_post_complete();
        };

        o.post_data = function(url, data) {
            exports.post_data(url, data,
                              this._on_post_success, this._on_post_failure);
        };

        /* initialize the action */
        o.init();
        o.clear_action();
        o.refresh_apply();

        $('#set-' + o.name + '-form').submit(function(e) {
            e.preventDefault();

            var pending_objects = [];
            o.table._for_each_checkbox(function() {
                if (!$(this).is(':checked'))
                    return;

                var id = o.table.id_from_checkbox($(this));
                pending_objects.push(id);
            });
            o._pending_posts += pending_objects.length;
            o.table._highlight_next_refresh(pending_objects);

            for (var i = 0; i < pending_objects.length; i++) {
                o.do_action(pending_objects[i]);
            }

            $('#' + o.name + '-action-dropdown').dropdown('toggle');
            o.clear_action();
        });


        return o;
    };

    /* JShint is warning that 'this' may be undefined in strict mode. What it
     * doesn't know is that dynatable will bind this when calling those
     * *_writer() functions */

    function select_writer(record) {
        return '<input type="checkbox" class="table-select">';
    }

    function series_writer(record) {
        var link = ctx.base_url + '/series/' + record.id + '/',
            title = record[this.id]; // jshint ignore:line

        if (title.length > 100)
            title = title.slice(0, 100) + '…';
        return '<a href="' + link + '">' + title + '</a>';
    }

    function test_state_writer(record) {
        var state = record.test_state;

        if (!state)
            return '';
        return "<span class='label result-" + state + "'>" + state + "</span>";
    }

    function date_writer(record) {
        return record[this.id].substr(0, 10);   // jshint ignore:line
    }

    function name_writer(record) {
        var path = this.id; // jshint ignore:line
        var name = get_value_from_path(record, path);
        if (!name)
            return '<em class="text-muted">None</span>';
        return name;
    }

    exports.amend_context = function(new_ctx) {
        $.extend(ctx, new_ctx);

        if (ctx.base_url.endsWith('/'))
            ctx.base_url = ctx.base_url.slice(0, -1);
        ctx.api_base_url = ctx.base_url + '/api/1.0';

        exports.user = ctx.user;
        exports.project = ctx.project;
    };

    exports.init = function(init_ctx) {
        setup_polyfills();

        this.amend_context(init_ctx);

        $.dynatableSetup({
            features: {
                perPageSelect: false,
            },
            dataset: {
                perPageDefault: ctx.user.items_per_page,
            },
            params: {
                perPage: 'perpage',
                records: 'results',
                sorts: 'ordering',
                queryRecordCount: 'count',
                totalRecordCount: 'count'
            },
            inputs: {
                pageText: '',
                paginationPrev: '«',
                paginationNext: '»',
                paginationGap: [1,1,1,1],
            },
            writers: {
                'select': select_writer,
                'name': series_writer,
                'last_updated': date_writer,
                'reviewer.name': name_writer,
                'submitter.name': name_writer,
                'test_state': test_state_writer,
            }
        });

        /* stop event propagation on some menus to keep them opened on click */
        $('.dropdown-menu.stop-propagation').click(function(e) {
            e.stopPropagation();
        });
    };

    Selectize.define('enter_key_submit', function (options) {
        var self = this;

        this.onKeyDown = (function (e) {
            var original = self.onKeyDown;

            return function (e) {
                var wasOpened = this.isOpen;
                original.apply(this, arguments);

                if (e.keyCode === 13 &&
                    (this.$control_input.val() !== '' || !wasOpened))
                    self.trigger('submit');
            };
        })();
    });

    exports.setup_autocompletion = function(selector, url) {
        return $(selector).selectize({
            valueField: 'pk',
            labelField: 'name',
            searchField: ['name', 'email'],
            plugins: ['enter_key_submit'],
            maxItems: 1,
            persist: false,
            onInitialize: function() {
                this.on('submit', function() {
                    if (!this.items.length)
                        this.$input.val(this.lastValue);
                    this.$input.closest('form').submit();
                }, this);
            },
            render: {
                option: function(item, escape) {
                    if (item.name)
                        return '<div><span class="completion-title">' +
                                    escape(item.name) + '</span>' +
                               '<small class="completion-details">' +
                                    escape(item.email) +
                               '</small></div>';
                    return '<div><span class="completion-title">' +
                               escape(item.email) + '</span></div>';
                },
                item: function(item, escape) {
                    if (item.name)
                        return '<div>' + escape(item.name) + '</div>';
                    return '<div>' + escape(item.email) + '</div>';
                }
            },
            load: function(query, callback) {
                if (query.length < 4)
                    return callback();

                $.ajax({
                    url: ctx.base_url + url +
                         '/?q=' + encodeURIComponent(query) + '&l=10',
                    error: function() {
                        callback();
                    },
                    success: function(res) {
                        callback(res);
                    }
                });
            }
        }).data('selectize');
    };

    exports.setup_series_list = function(selector, url, params) {
        var table = $(selector);

        var all_params = {
            ordering: '-last_updated',
            related: 'expand',
        };
        $.extend(all_params, params);

        if (typeof url == 'undefined') {
            url = '/projects/' + ctx.project.name + '/series/';
            if (!window.location.search)
                history.replaceState(null, null,
                        '?' + $.param({ ordering: all_params.ordering }));
        }

        exports.table = ctx.table = create_table({
            'ctx': ctx,
            'selector': selector,
            'name': 'series',
            'columns': {
                'ID': 'id',
                'Series': 'name',
                'Patches': 'n_patches',
                'Submitter': 'submitter.name',
                'Reviewer': 'reviewer.name',
                'Updated': 'last_updated',
                'Tests':'test_state',
            },
            'api_url': ctx.api_base_url + url,
            'api_params': all_params,
        });

        table.bind('dynatable:preinit', function(e, dynatable) {
            dynatable.utility.textTransform.PatchworkSeries = function(text) {
                return ctx.table.columns[text];
            };
        }).bind('dynatable:afterUpdate', function(e, rows) {
            ctx.table.on_update_finished();
        }).dynatable({
            features: {
                search: false,
                recordCount: false,
            },
            table: {
                defaultColumnIdStyle: 'PatchworkSeries',
                copyHeaderClass: true
            },
            dataset: {
                ajax: true,
                ajaxUrl: ctx.table.url(),
                ajaxOnLoad: false,
                records: []
            }
        });

        table.stickyTableHeaders();

        return ctx.table;
    };

    exports.patch_strip_series_marker = function(name) {
        var res = { order: '1', name: name };

        if (!name.startsWith('['))
            return res;

        var s = name.split(']');
        if (s.length == 1)
            return res;

        res.name = s.slice(1).join(']').trim();

        var tags = s[0].slice(1).split(',');
        for (var i = 0; i < tags.length; i++) {
            var matches = tags[i].match(/(\d+)\/(\d+)/);

            if (!matches)
                continue;

            res.order = matches[1];
            tags.splice(i, 1);
            break;
        }

        if (tags.length > 0)
            res.name = '[' + tags.join(',') + '] ' + res.name;

        return res;
    };

    exports.setup_series = function(config) {
        var column_num, column_name;

        column_num = $('#' + config.patches + ' tbody tr td:first-child');
        column_name = $('#' + config.patches + ' tbody tr td:nth-child(2) a');

        for (var i = 0; i < column_num.length; i++) {
            var name = $(column_name[i]).html();
            var res = this.patch_strip_series_marker(name);

            $(column_num[i]).html(res.order);
            $(column_name[i]).html(res.name);
        }
    };

    return exports;
}());
