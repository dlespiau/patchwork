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

    function date_writer(record) {
        return record[this.id].substr(0, 10);
    }

    function name_writer(record) {
        var path = this.id;
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

    return exports;
}());
