import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.events import fetch_managers, get_min_max_dates_from_schedule_events, fetch_driver_events_by_period_for_managers, fetch_driver_events_by_period_for_drivers, fetch_event_options, fetch_employees_in_schedule_event
from ui.components import create_data_table, create_modal, create_dropdown, create_date_range_picker
from utils.agg_utils import expand_events

dash.register_page(__name__, path='/events')

layout = html.Div([
    dcc.Tabs(id="event-tabs", value='manager-event-tab', children=[
        dcc.Tab(label='Manager View', value='manager-event-tab'),
        dcc.Tab(label='Driver View', value='driver-event-tab'),
    ], className="col-md-3 offset-md-1 col-12"),
    html.Div(id='event-tabs-content')
])

@callback(Output('event-tabs-content', 'children'),
          Input('event-tabs', 'value'))
def render_content(tab):
    if tab == 'manager-event-tab':
        min_date, max_date = get_min_max_dates_from_schedule_events()
        manager_options = fetch_managers().to_dict('records')
        event_options = fetch_event_options().to_dict('records')
        manager_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('event-date-range-picker', min_date, max_date),
                    create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=True, add_all=True),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                    dbc.Row([
                        dbc.Col(dcc.RadioItems(
                            id='scale-toggle',
                            options=[
                                {'label': 'Counts', 'value': 'count'},
                                {'label': 'Proportional', 'value': 'proportion'}
                            ],
                            value='count',
                            labelStyle={'display': 'inline-block'}
                        ), className="col-md-4 offset-md-4 col-12"),
                        dbc.Col(html.Button("Submit", id="manager-submit-button"), className="col-md-4 offset-md-4 col-12")
                    ], className="mb-3"),
                    dcc.Loading(html.Div(id='manager-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return manager_layout
    elif tab == 'driver-event-tab':
        min_date, max_date = get_min_max_dates_from_schedule_events()
        event_options = fetch_event_options().to_dict('records') 
        driver_layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    create_date_range_picker('event-date-range-picker', min_date, max_date),
                    create_dropdown('employee-dropdown', options=[], label='name', value='id', placeholder='Select driver', multi=True, add_all=False),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                    dbc.Row([
                        dbc.Col(dcc.RadioItems(
                            id='scale-toggle',
                            options=[
                                {'label': 'Counts', 'value': 'count'},
                                {'label': 'Proportional', 'value': 'proportion'}
                            ],
                            value='count',
                            labelStyle={'display': 'inline-block'}
                        ), className="col-md-4 offset-md-4 col-12"),
                        dbc.Col(html.Button("Submit", id="driver-submit-button"), className="col-md-4 offset-md-4 col-12")
                    ], className="mb-3"),
                    dcc.Loading(html.Div(id='driver-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return driver_layout

@callback(
    Output('manager-event-container', 'children'),
    State('event-date-range-picker', 'start_date'),
    State('event-date-range-picker', 'end_date'),
    State('manager-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('scale-toggle', 'value'),
    Input('manager-submit-button', 'n_clicks'),
    prevent_initial_callback=True
)
def render_manager_event_container(start_date, end_date, managers, events, scale, n_clicks):
    if not managers:
        return html.Div()
    if 'all' in managers:
        managers = None
    if n_clicks is None:
        return html.Div()
    df = fetch_driver_events_by_period_for_managers(start_date, end_date, managers)
    if df.empty:
        return dbc.Alert("No events found for the selected period and drivers.", color="warning")
    if events:
        df = df[df['event'].isin(events)]
    df = expand_events(df)
    df['week'] = df['date'].dt.isocalendar().week
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    total_event_col = df.groupby('manager').size().reset_index(name='total_manager_event_count')
    df = df.merge(total_event_col, on='manager', how='left')
    dfg = df.groupby(['manager', 'event']).agg({'event': 'count'}).rename(columns={'event': 'count'}).reset_index()
    dfg = pd.merge(dfg, total_event_col, on=['manager'], how='left')
    dfg['proportion'] = dfg['count'] / dfg['total_manager_event_count']
    dfg['proportion'] = dfg['proportion'].apply(lambda x: round(x, 3))
    dfg = dfg.sort_values(by=scale, ascending=False)
    
    manager_bars = []
    managers = dfg['manager'].unique()
    for manager in managers:
        manager_data = dfg[dfg['manager'] == manager]
        n_drivers = df[df['manager'] == manager]['employee'].nunique()
        bar_fig = px.bar(
            manager_data,
            x=scale,
            y='event', 
            color='event',
            title=f'{manager}<br><sub>{n_drivers} drivers between {start_date} and {end_date}</sub>',
            orientation='h'
        )
        bar_fig.update_layout(showlegend=False)
        bar_fig.update_layout(xaxis_type="log")
        if scale == 'proportion':
            bar_fig.update_layout(xaxis_tickformat=".1%")
            bar_fig.update_layout(xaxis_tickangle=-45)
        manager_bars.append((n_drivers, dbc.Col(dcc.Graph(figure=bar_fig), width=6)))
    
    manager_bars.sort(key=lambda x: x[0], reverse=True)
    sorted_bars = [bar for _, bar in manager_bars]
    
    return dcc.Loading([
        dbc.Row(sorted_bars),
    ], type='circle')

@callback(
    Output('driver-event-container', 'children'),
    State('event-date-range-picker', 'start_date'),
    State('event-date-range-picker', 'end_date'),
    State('employee-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('scale-toggle', 'value'),
    Input('driver-submit-button', 'n_clicks'),
    prevent_initial_callback=True
)
def render_driver_event_container(start_date, end_date, drivers, events, scale, n_clicks):
    if not drivers:
        return html.Div()
    if 'all' in drivers:
        drivers = None
    if n_clicks is None:
        return html.Div()
    
    df = fetch_driver_events_by_period_for_drivers(start_date, end_date, drivers)
    if df.empty:
        return dbc.Alert("No events found for the selected period and drivers.", color="warning")
    
    if events:
        df = df[df['event'].isin(events)]
    
    df = expand_events(df)
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    driver_bars = []
    for driver in df['employee'].unique():
        driver_data = df[df['employee'] == driver]
        
        # Weekly aggregation
        total_event_col = driver_data.groupby('week').size().reset_index(name='total_event_count')
        dfg = driver_data.groupby(['week', 'event']).agg({'event': 'count'}).rename(columns={'event': 'count'}).reset_index()
        dfg = pd.merge(dfg, total_event_col, on=['week'], how='left')
        dfg['proportion'] = dfg['count'] / dfg['total_event_count']
        dfg['proportion'] = dfg['proportion'].apply(lambda x: round(x, 3))
        dfg = dfg.sort_values(by=['week', scale], ascending=[True, False])
        
        # Weekly bar graphs
        for week in dfg['week'].unique():
            week_data = dfg[dfg['week'] == week]
            if week_data.empty:
                continue
            bar_fig = px.bar(
                week_data,
                x=scale,
                y='event', 
                color='event',
                title=f'{driver} - Week {week}',
                orientation='h'
            )
            bar_fig.update_layout(showlegend=False)
            bar_fig.update_layout(xaxis_type="log")
            if scale == 'proportion':
                bar_fig.update_layout(xaxis_tickformat=".1%")
                bar_fig.update_layout(xaxis_tickangle=-45)
            driver_bars.append(dbc.Col(dcc.Graph(figure=bar_fig), width=6))
        
        # Global aggregation
        global_data = driver_data.groupby('event').agg({'event': 'count'}).rename(columns={'event': 'count'})
        global_data['proportion'] = global_data['count'] / global_data['count'].sum()
        global_data['proportion'] = global_data['proportion'].apply(lambda x: round(x, 3))
        global_data = global_data.reset_index()
        global_data = global_data.sort_values(by=scale, ascending=False)
        
        # Global bar graph
        global_bar_fig = px.bar(
            global_data,
            x=scale,
            y='event',
            color='event',
            title=f'{driver} - Event Distribution from {start_date} to {end_date}',
            orientation='h'
        )
        global_bar_fig.update_layout(showlegend=False)
        global_bar_fig.update_layout(xaxis_type="log")
        if scale == 'count':
            global_bar_fig.update_layout(yaxis_title="Event Count")
        if scale == 'proportion':
            global_bar_fig.update_layout(xaxis_title="Event Proportion")
            global_bar_fig.update_layout(xaxis_tickformat=".1%")
            global_bar_fig.update_layout(xaxis_tickangle=-45)
        driver_bars.append(dbc.Col(dcc.Graph(figure=global_bar_fig), width=12))
    
    return dcc.Loading([
        dbc.Row(driver_bars),
    ], type='circle')

@callback(
    Output('employee-dropdown', 'options'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date')
)
def update_driver_options(start_date, end_date):
    if not start_date or not end_date:
        return []
    df = fetch_employees_in_schedule_event(start_date, end_date)
    df.sort_values(by='name', inplace=True)
    driver_options = df.to_dict('records')
    driver_options = [{'label': driver['name'], 'value': driver['id']} for driver in driver_options]
    return driver_options