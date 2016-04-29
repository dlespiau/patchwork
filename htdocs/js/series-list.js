$(function () {
    'use strict';

    var series_table = pw.setup_series_list('#serieslist');

    /* status filter */
    pw.create_filter({
        table: series_table,
        name: 'status',
        change_background_on_apply: false,
        init: function() {
            var _this = this;

            this.initial = $('#status-new');
            this.in_progress = $('#status-in-progress');
            this.done = $('#status-done');
            this.incomplete = $('#status-incomplete');

            $('#status-filter input:checkbox').change(function() {
                _this.refresh_apply();
            });
        },
        _collect_states: function() {
            var filters = [];

            if (this.initial.prop('checked'))
                filters.push('initial');
            if (this.in_progress.prop('checked'))
                filters.push('in progress');
            if (this.done.prop('checked'))
                filters.push('done');
            if (this.incomplete.prop('checked'))
                filters.push('incomplete');

            return filters;
        },
        set_filter: function(table) {
            var filters = this._collect_states();

            table.set_filter('state', filters.join(','));
        },
        reset_filter: function(table) {
            this.initial.prop('checked', true);
            this.in_progress.prop('checked', true);
            this.done.prop('checked', false);
            this.incomplete.prop('checked', true);
            this.set_filter(table);
            return true;
        },
        can_submit: function() {
            return this._collect_states().length > 0;
        },
        humanize: function() {
            var transform = {
                'initial': "'new'",
                'in progress': "'in progress'",
                'done': "'done'",
                'incomplete': "'incomplete'",
            };
            var filters = this._collect_states();

            var states = [];
            for (var i = 0; i < filters.length; i++) {
                states.push(transform[filters[i]]);
            }

            return 'with status: ' + states.join(', ');
        },
    });


    /* date filter */
    pw.create_filter({
        table: series_table,
        name: 'date',
        init: function() {
            var _this = this;

            $('.input-group.date').datepicker({
                clearBtn: true,
                todayHighlight: true,
                autoclose: true,
                format: 'yyyy-mm-dd',

            });

            $('.input-group.date').datepicker().on('changeDate', function(e) {
                _this.refresh_apply();
            });

        },
        set_filter: function(table) {
            table.set_filter('updated_since', $('#date-from').val());
            table.set_filter('updated_before', $('#date-to').val());
        },
        reset_filter: function(table) {
            $('.input-group.date').datepicker('update', '');
            table.set_filter('updated_since', null);
            table.set_filter('updated_before', null);
        },
        can_submit: function() {
            return $('#date-from').val().trim() ||
                   $('#date-to').val().trim();
        },
        humanize: function() {
            var from = $('#date-from').val().trim(),
                to = $('#date-to').val().trim();

            if (from && to)
                return 'updated between ' + from + ' and ' + to;
            else if (from)
                return 'updated since ' + from;
            else if (to)
                return 'updated before ' + to;
            return null;
        },
    });

    /* submitter filter */
    pw.create_filter({
        table: series_table,
        name: 'submitter',
        init: function() {
            var _this = this;

            this.me = $('#submitter-me');
            this.by = $('#submitter-by');
            /* don't show the "submitted by me" option if there is no logged
             * in user */
            if (!pw.user.is_authenticated)
                this.set_radio_disabled(this.me, true);

            $('#submitter-filter input:radio').change(function() {
                _this.refresh_apply();
            });

            this.completion = pw.setup_autocompletion('#submitter-search',
                                                      '/submitter');
            this.completion.on('change', function() {
                _this.refresh_apply();
            });

            $('#submitter-filter .selectize-input input').focus(function() {
                _this.me.prop('checked', false);
                _this.by.prop('checked', true);
                _this.refresh_apply();
            });
        },
        set_filter: function(table) {
            var filter = null;
            var submitter = this.completion.getValue();

            if (this.me.prop('checked'))
                filter = 'self';
            else if (this.by.prop('checked') && submitter)
                filter = submitter;

            table.set_filter('submitter', filter);
        },
        reset_filter: function(table) {
            this.me.prop('checked', false);
            this.by.prop('checked', true);
            table.set_filter('submitter', null);
            this.completion.clearOptions();
            this.completion.clear();
        },
        can_submit: function() {
            return this.me.prop('checked') ||
                   (this.by.prop('checked') && this.completion.getValue());
        },
        humanize: function() {
            if (this.me.prop('checked'))
                return 'submitted by me';
            var submitter = this.completion.getValue();
            return 'submitted by ' + this.completion.getItem(submitter).text();
        },
    });

    /* reviewer filter */
    pw.create_filter({
        table: series_table,
        name: 'reviewer',
        init: function() {
            var _this = this;

            this.none = $('#reviewer-none');
            this.me = $('#reviewer-me');
            this.to = $('#reviewer-to');
            /* don't show the "reviewed by me" option if there is no logged
             * in user */
            if (!pw.user.is_authenticated)
                this.set_radio_disabled(this.me, true);

            $('#reviewer-filter input:radio').change(function() {
                _this.refresh_apply();
            });

            this.completion = pw.setup_autocompletion('#reviewer-search',
                                                      '/complete_user');
            this.completion.on('change', function() {
                _this.refresh_apply();
            });

            $('#reviewer-filter .selectize-input input').focus(function() {
                _this.none.prop('checked', false);
                _this.me.prop('checked', false);
                _this.to.prop('checked', true);
                _this.refresh_apply();
            });
        },
        set_filter: function(table) {
            var filter = null;
            var reviewer = this.completion.getValue();

            if (this.none.prop('checked'))
                filter = 'null';
            else if (this.me.prop('checked'))
                filter = pw.user.pk;
            else if (this.to.prop('checked') && reviewer)
                filter = reviewer;

            table.set_filter('reviewer', filter);
        },
        reset_filter: function(table) {
            this.none.prop('checked', false);
            this.me.prop('checked', false);
            this.to.prop('checked', true);
            table.set_filter('reviewer', null);
            this.completion.clearOptions();
            this.completion.clear();
        },
        can_submit: function() {
            return this.none.prop('checked') || this.me.prop('checked') ||
                   (this.to.prop('checked') && this.completion.getValue());
        },
        humanize: function() {
            if (this.none.prop('checked'))
                return 'with no reviewer';
            if (this.me.prop('checked'))
                return 'assigned to me for review';
            var reviewer = this.completion.getValue();
            return 'assigned for review to ' + this.completion.getItem(reviewer).text();
        },
    });

    /* tests filter */
    pw.create_filter({
        table: series_table,
        name: 'tests',
        init: function() {
            var _this = this;

            this.success = $('#tests-success');
            this.warning = $('#tests-warning');
            this.failure = $('#tests-failure');
            this.info = $('#tests-info');

            $('#tests-filter input:checkbox').change(function() {
                _this.refresh_apply();
            });
        },
        _collect_states: function() {
            var filters = [];

            if (this.success.prop('checked'))
                filters.push('success');
            if (this.warning.prop('checked'))
                filters.push('warning');
            if (this.failure.prop('checked'))
                filters.push('failure');
            if (this.info.prop('checked'))
                filters.push('info');

            return filters;
        },
        set_filter: function(table) {
            var filters = this._collect_states();

            table.set_filter('test_state', filters.join(','));
        },
        reset_filter: function(table) {
            this.success.prop('checked', false);
            this.warning.prop('checked', false);
            this.failure.prop('checked', false);
            this.info.prop('checked', false);
            table.set_filter('test_state', null);
        },
        can_submit: function() {
            return this.success.prop('checked') ||
                   this.warning.prop('checked') ||
                   this.info.prop('checked') ||
                   this.failure.prop('checked');
        },
        humanize: function() {
            var filters = this._collect_states();

            if (filters.length == 1)
                return 'with test result "' + filters[0] + '"';
            if (filters.length == 2)
                return 'with test result "' + filters[0] + '" or "' +
                    filters[1] + '"';
            if (filters.length == 3)
                return 'with test result "' + filters[0] + '", "' +
                    filters[1] + '" or "' + filters[2] + '"';
        },
    });

    /* tests filter */
    pw.create_search_filter({
        table: series_table,
        name: 'search',
        init: function() {
            this.input = $('#search-series');
        },
        set_filter: function(table) {
            table.set_filter('name', this.input.val());
        },
        reset_filter: function(table) {
            this.input.val('');
            table.set_filter('name', null);
        },
        can_submit: function() {
            var val = this.input.val();
            return val && val.length > 0;
        },
        humanize: function() {
            return 'containing "' + this.input.val() + '"';
        },
    });

    /* reviewer action */
    pw.create_action({
        table: series_table,
        name: 'reviewer',
        init: function() {
            var _this = this;

            this.none = $('#set-reviewer-none');
            this.me = $('#set-reviewer-me');
            this.to = $('#set-reviewer-to');

            /* don't allow the "assign to me" option if there is no logged in
             * user */
            if (!pw.user.is_authenticated)
                this.set_radio_disabled(this.me, true);

            $('#reviewer-action input:radio').change(function() {
                _this.refresh_apply();
            });

            this.completion = pw.setup_autocompletion('#set-reviewer-search',
                                                      '/complete_user');
            this.completion.on('change', function() {
                _this.refresh_apply();
            });

            $('#reviewer-action .selectize-input input').focus(function() {
                _this.me.prop('checked', false);
                _this.to.prop('checked', true);
                _this.refresh_apply();
            });

            /* enable/disable the "unassign" radio button */
            $(this.table.selector).on('table-row-selection-changed',
                                      function() {
                var n_reviewers = 0;

                _this.table.for_each_selected_row(function(series)  {
                    if (series.reviewer)
                        n_reviewers++;
                });

                _this.set_radio_disabled(_this.none, n_reviewers === 0);
            });
        },
        do_action: function(id) {
            var reviewer = null;

            if (this.none.prop('checked'))
                reviewer = null;
            else if (this.me.prop('checked'))
                reviewer = pw.user.pk;
            else
                reviewer = this.completion.getValue();

            this.patch_data('/series/' + id + '/', { reviewer: reviewer });
        },
        clear_action: function() {
            this.none.prop('checked', false);
            this.me.prop('checked', false);
            this.to.prop('checked', true);
            this.completion.clearOptions();
            this.completion.clear();
        },
        can_submit: function() {
            return this.none.prop('checked') || this.me.prop('checked') ||
                   (this.to.prop('checked') && this.completion.getValue());
        },

    });

    /* test action */
    pw.create_action({
        table: series_table,
        name: 'test',
        init: function() {},
        do_action: function(id, revision) {
            this.post_data('/series/' + id + '/revisions/' + revision +
                           '/newrevision/');
        },
        clear_action: function() {},
        can_submit: function() { return true; },
    });

    /* initial load */
    series_table.refresh();
});
