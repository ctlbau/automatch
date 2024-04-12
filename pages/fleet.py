import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.fleetpulse.db_support import fetch_managers, fetch_statuses, fetch_centers, fetch_vehicles, fetch_plates, select_plate
from ui.components import *
from utils.agg_utils import calculate_aggregations, calculate_status_periods, filter_and_format, sanity_check

dash.register_page(__name__, path='/fleet')

######## Begin Layout ##########
layout = html.Div([
    # create_navbar('Fleet Pulse'),
    dcc.Tabs(id="tabs", value='manager-tab', children=[
        dcc.Tab(label='Manager View', value='manager-tab'),
        dcc.Tab(label='Vehicle view', value='vehicle-tab'),
    ], className="col-md-3 offset-md-1 col-12"),
    html.Div(id='tabs-content'),
])
######## End Layout ############


############ Begin Render UI ############
@callback(
    Output('tabs-content', 'children'),
    [
        Input('tabs', 'value')
    ]
)
def render_ui(tab):
    if tab == 'manager-tab':
        centers = fetch_centers().to_dict('records')
        # TODO: refactor filters with generic create_filter
        return [
            manager_filter,
            create_company_filter('company-dropdown'),
            create_dropdown('center-dropdown', centers, 'Select center', multi=True),
            create_status_filter('status-dropdown'),
            create_date_range_picker('date-picker-range'),
            create_navbar_options('count-proportion-radio'),
            html.Div(id='manager-view-graph-and-table-container', className="col-md-9 offset-md-2 col-12"),
            create_modal('details-modal-all', 'details-modal-title-all', 'modal-content-all', 'modal-footer-all'),
            create_modal('details-modal-part', 'details-modal-title-part', 'modal-content-part', 'modal-footer-part'),
        ]
    elif tab == 'vehicle-tab':
        return [
            create_plate_filter('plate-dropdown'),
            create_date_range_picker('date-picker-range'),
            html.Div(id='vehicle-view-graph-container', className="col-md-9 offset-md-2 col-12")
        ]
########## End Render UI ###########

########## Begin Dropdown Options ##########
@callback(
    [Output('manager-dropdown', 'options'),
     Output('status-dropdown', 'options')],
    [Input('tabs', 'value')]
)
def set_in_managerview_manager_and_status_dropdown(tab):
    statuses = fetch_statuses()
    managers = fetch_managers()
    status_options = [
        {'label': status, 'value': status} for status in statuses['status']
        ]
    manager_options = [
            {'label': manager, 'value': manager} for manager in managers['name']
            ]
    manager_options.insert(0, {'label': 'All Managers', 'value': 'all'})

    if tab != 'manager-tab':
        return [], []
    return manager_options, status_options

@callback(
    Output('plate-dropdown', 'options'),
    [Input('tabs', 'value')]
)
def update_plate_dropdown(tab):
    if tab != 'vehicle-tab':
        return dash.no_update

    plates = fetch_plates()

    plate_options = [{'label': plate, 'value': plate} for plate in plates['plate']]

    return plate_options
########## End Dropdown Options ##########



@callback(
    Output('manager-view-graph-and-table-container', 'children'),
    [
        Input('tabs', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        Input('company-dropdown', 'value'),
        Input('center-dropdown', 'value'),
        Input('manager-dropdown', 'value'),
        Input('status-dropdown', 'value'),
        Input('count-proportion-radio', 'value'),
    ],
    [State('status-dropdown', 'options')]
)
def update_managerview_table_and_graph(tab, start_date, end_date, selected_company, selected_centers, selected_manager, selected_statuses, count_proportion_radio, status_options):
    if tab != 'manager-tab':
        return dash.no_update

    base_df = fetch_vehicles(selected_centers, company=selected_company, from_date=start_date, to_date=end_date)
    agg_df = calculate_aggregations(base_df, ['date', 'status'])
    table_page_size = len(selected_statuses) if selected_statuses else len(status_options)

    if 'all' == selected_manager:

        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
            agg_df = agg_df[agg_df['status'].isin(selected_statuses)]

        pivot_df = agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = agg_df[['status', 'total_unique']].drop_duplicates()
        pivot_df = pivot_df.merge(total_unique_per_status, on='status', how='left')
        pivot_df.columns = pivot_df.columns.astype(str)
        pivot_columns = pivot_df.columns[1:]
        for col in pivot_columns:
            pivot_df[col] = pivot_df[col].apply(lambda x: round(x, 3))
        csv_filename = 'all_managers_from_' + start_date + '_to_' + end_date + '.csv'
        table = create_data_table('main-table-all', pivot_df, csv_filename, table_page_size)
        download_button = html.Button('Download CSV', id='download-main-table-all-csv', n_clicks=0)
        fig = create_line_graph(agg_df, count_proportion_radio) # There is also an option for a grouped bar graph

        return [fig, table, download_button]

    else:

        if selected_manager:
            base_df = base_df[base_df['manager'] == selected_manager]
        else:
            return dash.no_update

        if selected_statuses:
            base_df = base_df[base_df['status'].isin(selected_statuses)]
        manager_agg_df = calculate_aggregations(base_df, ['date', 'status'])
        manager_pivot_df = manager_agg_df.pivot(index='status', columns='date', values=count_proportion_radio).reset_index().fillna(0)
        total_unique_per_status = manager_agg_df[['status', 'total_unique']].drop_duplicates()
        manager_pivot_df = manager_pivot_df.merge(total_unique_per_status, on='status', how='left')
        manager_pivot_df.columns = manager_pivot_df.columns.astype(str)

        csv_filename = selected_manager + '_from_' + start_date + '_to_' + end_date + '.csv'
        table = create_data_table('main-table-part', manager_pivot_df, csv_filename, table_page_size)
        download_button = html.Button('Download CSV', id='download-main-table-part-csv', n_clicks=0)
        fig = create_line_graph(manager_agg_df, count_proportion_radio)

        return [fig, table, download_button]
    
@callback(Output('main-table-all', 'exportDataAsCsv'),
         [Input('download-main-table-all-csv', 'n_clicks')])
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(Output('main-table-part', 'exportDataAsCsv'),
            [Input('download-main-table-part-csv', 'n_clicks')])
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
    Output('details-modal-all', 'is_open'),
    Output('details-modal-title-all', 'children'),
    Output('modal-content-all', 'children'),
    Output('modal-footer-all', 'children'),
    [
        Input('main-table-all', 'cellClicked'),
        State('main-table-all', 'selectedRows'),
        State('company-dropdown', 'value'),
        State('center-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('status-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_all(clicked_cell, clicked_row, companies, selected_centers, start_date, end_date, selected_statuses, count_proportion_radio):
    if not clicked_cell:
        return False, "", [], []

    column_selected = clicked_cell['colId']
    status = clicked_row[0]['status']
    
    base_df = fetch_vehicles(selected_centers, company=companies, from_date=start_date, to_date=end_date)
    if base_df is None or base_df.empty:
        return False, "", [], []
    
    status_df = base_df[base_df['status'] == status].copy()

    if column_selected == 'total unique':
        streaks_df = calculate_status_periods(status_df)
        status_df = status_df.merge(streaks_df, on='plate', how='left')
        status_df.drop(['date', 'status', 'date_diff', 'status_change', 'group'], axis=1, inplace=True)
        status_df.drop_duplicates(subset=['plate'], inplace=True)
        modal_title = f"Overview of {len(status_df)} vehicles that have been, at some point, in {status} status between {start_date} and {end_date}"
        csv_filename = f'{status}_from_{start_date}_to_{end_date}.csv'
        table = create_data_table(f'modal-content-all-total-unique', status_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-total-unique-csv', n_clicks=0)

        return True, modal_title, table, download_button
    
    elif column_selected == 'status':
        return False, "", [], []

    else:
        date = pd.to_datetime(column_selected).date()
        filtered_df = filter_and_format(status_df, date, status)

        if filtered_df.empty:
            return False, "", [], []

        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"
        csv_filename = f"{status}_on_{date.strftime('%Y-%m-%d')}.csv"
        table = create_data_table(f'modal-content-status', filtered_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-status-csv', n_clicks=0)

    return True, modal_title, table, download_button

@callback(Output('modal-content-all-total-unique', 'exportDataAsCsv'),
         Input('download-modal-table-total-unique-csv', 'n_clicks'),
         prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(Output('modal-content-status', 'exportDataAsCsv'),
            Input('download-modal-table-status-csv', 'n_clicks'),
            prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update


@callback(
    Output('details-modal-part', 'is_open'),
    Output('details-modal-title-part', 'children'),
    Output('modal-content-part', 'children'),
    Output('modal-footer-part', 'children'),
    [
        Input('main-table-part', 'cellClicked'),
        State('main-table-part', 'selectedRows'),
        State('company-dropdown', 'value'),
        State('center-dropdown', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('status-dropdown', 'value'),
        State('manager-dropdown', 'value'),
        State('count-proportion-radio', 'value'),
    ]
)
def update_modal_part(clicked_cell, clicked_row, companies, selected_centers, start_date, end_date, selected_statuses, selected_manager, count_proportion_radio):
    if not clicked_cell:
        return False, "", [], []

    column_selected = clicked_cell['colId']
    status = clicked_row[0]['status']
    
    base_df = fetch_vehicles(selected_centers, company=companies, from_date=start_date, to_date=end_date)
    if base_df is None or base_df.empty:
        return False, "", [], []
    
    status_df = base_df[base_df['status'] == status].copy()
    if selected_manager:
        status_df = status_df[status_df['manager'] == selected_manager]

    if column_selected == 'total unique':
        streaks_df = calculate_status_periods(status_df)
        status_df = status_df.merge(streaks_df, on='plate', how='left')
        # status_df['date'] = status_df['date'].dt.strftime('%Y-%m-%d')
        status_df.drop(['date','status', 'date_diff', 'status_change', 'group'], axis=1, inplace=True)
        status_df.drop_duplicates(subset=['plate'], inplace=True)
        modal_title = f"Overview of {len(status_df)} vehicles that have been, at some point, in {status} status between {start_date} and {end_date}"
        csv_filename = f'{status}_between_{start_date}_and_{end_date}_for_{selected_manager}.csv'
        table = create_data_table(f'modal-content-part-total-unique', status_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-table-status-csv', n_clicks=0)

        return True, modal_title, table, download_button
    
    elif column_selected == 'status':
        return False, "", [], []

    else:
        date = pd.to_datetime(column_selected).date()
        filtered_df = filter_and_format(status_df, date, status)

        if filtered_df.empty:
            return False, "", [], []

        csv_filename = f"{status}_on_{date.strftime('%Y-%m-%d')}_for_{selected_manager}.csv"
        table = create_data_table(f'modal-content-part-date', filtered_df, csv_filename, 10)
        download_button = html.Button('Download CSV', id='download-modal-date-table', n_clicks=0)
        modal_title = f"Found {len(filtered_df)} {status} vehicles on {date.strftime('%Y-%m-%d')}"

    return True, modal_title, table, download_button

@callback(Output('modal-content-part-total-unique', 'exportDataAsCsv'),
         Input('download-modal-table-status-csv', 'n_clicks'),
         prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(Output('modal-content-part-date', 'exportDataAsCsv'),
            Input('download-modal-date-table', 'n_clicks'),
            prevent_initial_call=True)
def download_csv(n_clicks):
    if n_clicks > 0:
        return True
    return dash.no_update

@callback(
    Output('vehicle-view-graph-container', 'children'),
    [
        Input('tabs', 'value'),
        Input('plate-dropdown', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_vehicle_view(tab, selected_plate, start_date, end_date):
    if tab != 'vehicle-tab':
        return dash.no_update

    df = select_plate(
        plate=selected_plate,
        from_date=start_date,
        to_date=end_date
    )

    # Create a line graph showing the status of the vehicle over time
    fig = px.line(df, x='date', y='status', title='Vehicle Status Over Time', markers=True)
    fig.update_layout(height=400, xaxis_tickangle=-45)
    fig.update_xaxes(tickformat="%Y-%m-%d")

    return dbc.Row([dbc.Col(dcc.Graph(figure=fig), width=12)])
