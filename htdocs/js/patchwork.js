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

    function setup_polyfills() {
        setup_polyfill_endswith();
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
            api_base_url: '/api/1.0',
            project: null,
            user : {
                items_per_page: 100,
            },
        };

    var columnsMap = {
        'Series': 'name',
        'Patches': 'n_patches',
        'Submitter': 'submitter.name',
        'Reviewer': 'reviewer.name',
        'Submitted': 'submitted',
        'Updated': 'last_updated'
    };

    /* JShint is warning that 'this' may be undefined in strict mode. What it
     * doesn't know is that dynatable will bind this when calling those
     * *_writer() functions */

    function series_writer(record) {
        return '<a href="/series/' + record.id + '/">' +
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

        if (ctx.api_base_url.endsWith('/'))
            ctx.api_base_url = ctx.api_base_url.slice(0, -1);

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
                paginationPrev: '« Previous',
                paginationNext: 'Next »',
                paginationGap: [1,1,1,1],
            },
            writers: {
                'name': series_writer,
                'submitted': date_writer,
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
        url = ctx.api_base_url + url + '?' + $.param({
            ordering: ordering,
            related: 'expand'
        });

        table.bind('dynatable:preinit', function(e, dynatable) {
            dynatable.utility.textTransform.PatchworkSeries = function(text) {
                return columnsMap[text];
            };
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
                ajaxUrl: url,
                ajaxOnLoad: true,
                records: []
            }
        });

        table.stickyTableHeaders();
    };

    exports.setup_series = function(config) {
        var column_num, column_name;

        column_num = $('#' + config.patches + ' tbody tr td:first-child');
        column_name = $('#' + config.patches + ' tbody tr td:nth-child(2) a');

        for (var i = 0; i < column_num.length; i++) {
            var name = $(column_name[i]).html();
            var s = name.split(']');

            if (s.length == 1) {
                $(column_num[i]).html('1');
            } else {
                var matches = s[0].match(/(\d+)\/(\d+)/);

                $(column_name[i]).html(s.slice(1).join(']'));

                if (!matches) {
                    $(column_num[i]).html('1');
                    continue;
                }

                $(column_num[i]).html(matches[1]);
            }
        }
    };

    return exports;
}());
