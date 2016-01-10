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

    var exports = {},
        ctx = {
            base_url: '',
            api_base_url: '/api/1.0',
            project: null,
            user : {
                items_per_page: 100,
            },
            table: null,
        };

    function create_table(config) {
        var o = {
            filters: [],
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

        o.refresh_info = function(content) {
            var descriptions = [];

            for (var i = 0; i < this.filters.length; i++) {
                var filter = this.filters[i];

                if (!filter.is_active)
                    continue;

                descriptions.push(filter.humanize());
            }

            var text, count = this.count();
            if (descriptions.length === 0)
                text = "Showing all " + count + " " + this.name;
            else {
                text = "Showing " + count + " " + this.name + ' ';
                text += descriptions.join(', ');
            }
            this.set_info(text);
        };

        /* called when dynatable has finished populating the DOM */
        o.on_update_finished = function() {
            this.refresh_info();
        };

        return o;
    }

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

        o.set_active = function(val) {
            if (val == o.is_active)
                return;

            o.is_active = val;
            o.refresh_active();
        };

        /* initialize the filter */
        o.init();

        $('#' + o.name + '-form').submit(function(e) {
            e.preventDefault();

            o.set_filter(o.table);

            o.table.refresh();
            $('#' + o.name + '-filter-dropdown').dropdown('toggle');

            o.set_active(true);
        });

        o._clear_filter = function() {
            o.clear_filter(this.table);
            this.table.refresh();
            o.set_active(false);
        };

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

    /* JShint is warning that 'this' may be undefined in strict mode. What it
     * doesn't know is that dynatable will bind this when calling those
     * *_writer() functions */

    function series_writer(record) {
        var link = ctx.base_url + '/series/' + record.id + '/';
        return '<a href="' + link + '">' +
               record[this.id] + // jshint ignore:line
               '</a>';
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
    };

    exports.init = function(init_ctx) {
        setup_polyfills();

        this.amend_context(init_ctx);

        if (ctx.base_url.endsWith('/'))
            ctx.base_url = ctx.base_url.slice(0, -1);
        ctx.api_base_url = ctx.base_url + '/api/1.0';

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
                'name': series_writer,
                'last_updated': date_writer,
                'reviewer.name': name_writer,
                'submitter.name': name_writer
            }
        });
    };

    exports.setup_series_list = function(selector, url, ordering) {
        var table = $(selector);

        if (typeof ordering == 'undefined')
            ordering = '-last_updated';

        if (typeof url == 'undefined') {
            url = '/projects/' + ctx.project + '/series/';
            if (!window.location.search)
                history.replaceState(null, null,
                                     '?' + $.param({ ordering: ordering }));
        }

        exports.table = ctx.table = create_table({
            'selector': selector,
            'name': 'series',
            'columns': {
                'ID': 'id',
                'Series': 'name',
                'Patches': 'n_patches',
                'Submitter': 'submitter.name',
                'Reviewer': 'reviewer.name',
                'Updated': 'last_updated'
            },
            'api_url': ctx.api_base_url + url,
            'api_params': {
                related: 'expand',
            }
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
                ajaxOnLoad: true,
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
