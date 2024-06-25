import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.events import fetch_managers, get_min_max_dates_from_schedule_events, fetch_driver_events_by_period_for_managers, fetch_driver_events_by_period_for_drivers, fetch_event_options, fetch_employees_in_schedule_event
from ui.components import create_data_table, create_modal, create_dropdown, create_date_range_picker
from utils.agg_utils import expand_events
from datetime import date

dash.register_page(__name__, path='/events')

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Tabs(id="event-tabs", active_tab='manager-event-tab', children=[
                dbc.Tab(label='Manager View', tab_id='manager-event-tab'),
                dbc.Tab(label='Driver View', tab_id='driver-event-tab'),
                dbc.Tab(label='Event View', tab_id='event-event-tab'),
            ], className="mb-3 sidebar-adjacent-tabs"),
            html.Div(id='event-tabs-content')
        ], className="p-0")
    ], className="g-0")
], fluid=True, className="p-0")


@callback(Output('event-tabs-content', 'children'),
          Input('event-tabs', 'active_tab'))
def render_content(tab):
    min_date, max_date = get_min_max_dates_from_schedule_events()
    if tab == 'event-event-tab':
        return create_event_layout(min_date, max_date)
    elif tab == 'driver-event-tab':
        event_options = fetch_event_options().to_dict('records')
        return create_driver_layout(min_date, max_date, event_options)
    else:
        manager_options = fetch_managers().to_dict('records')
        event_options = fetch_event_options().to_dict('records')
        return create_manager_layout(min_date, max_date, manager_options, event_options)

def create_event_layout(min_date, max_date):
    manager_options = fetch_managers().to_dict('records')
    event_options = fetch_event_options().to_dict('records')

    event_layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        create_date_range_picker('event-date-range-picker', min_date, max_date),
                        create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=True, add_all=True),
                        create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                        dbc.Row([
                            dbc.Col(dbc.RadioItems(
                                id='scale-toggle',
                                options=[
                                    {'label': 'Counts', 'value': 'count'},
                                    {'label': 'Proportional', 'value': 'proportion'}
                                ],
                                value='count',
                                inline=True
                            ), width=6),
                            dbc.Col(dbc.Button("Submit", id="event-submit-button", color="primary"), width=6)
                        ], className="mb-3"),
                    ])
                ], className="mb-3"),
            ], width=4),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Spinner(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id='event-event-container', children=[])
                        ])
                    ], id='event-event-card', style={'display': 'none'}, className="mb-3"),
                    color="primary",
                    type="border",
                ),
            ], width=12),
        ]),
    ], fluid=True, className="p-0")
    return event_layout
@callback(
    Output('event-event-container', 'children'),
    Output('event-event-card', 'style'),
    State('event-date-range-picker', 'start_date'),
    State('event-date-range-picker', 'end_date'),
    State('manager-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('scale-toggle', 'value'),
    Input('event-submit-button', 'n_clicks'),
    prevent_initial_callback=True
)
def render_manager_event_container(start_date, end_date, managers, events, scale, n_clicks):
    if not managers or n_clicks is None:
        return [], {'display': 'none'}
    if 'all' in managers:
        managers = None
    
    df = fetch_driver_events_by_period_for_managers(start_date, end_date, managers)
    if df.empty:
        return dbc.Alert("No events found for the selected period and drivers.", color="warning"), {'display': 'block'}
    if events:
        df = df[df['event'].isin(events)]
    df = expand_events(df)
    df = df[(df['date'] >= pd.to_datetime(start_date).date()) & (df['date'] <= pd.to_datetime(end_date).date())]
    total_event_col = df.groupby('manager').size().reset_index(name='total_manager_event_count')
    df = df.merge(total_event_col, on='manager', how='left')
    dfg = df.groupby(['manager', 'event']).agg({'event': 'count'}).rename(columns={'event': 'count'}).reset_index()
    dfg = pd.merge(dfg, total_event_col, on=['manager'], how='left')
    dfg['proportion'] = dfg['count'] / dfg['total_manager_event_count']
    dfg['proportion'] = dfg['proportion'].apply(lambda x: round(x, 3))
    dfg = dfg.sort_values(by=scale, ascending=False)

    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(dfg['event'].unique())}
    
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
            color_discrete_map=event_colors,
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
    
    return dbc.Row(sorted_bars), {'display': 'block'}

def create_manager_layout(min_date, max_date, manager_options, event_options):
    manager_layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        create_date_range_picker('event-date-range-picker', min_date, max_date),
                        create_dropdown('man-event-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=True, add_all=True),
                        create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                        dbc.Row([
                            dbc.Col(dbc.RadioItems(
                                id='scale-toggle',
                                options=[
                                    {'label': 'Counts', 'value': 'count'},
                                    {'label': 'Proportional', 'value': 'proportion'}
                                ],
                                value='proportion',
                                inline=True
                            ), width=6),
                            dbc.Col(dbc.Button("Submit", id="manager-submit-button", color="primary"), width=6)
                        ], className="mt-3"),
                    ])
                ], className="mb-3"),
            ], width=4),
            dbc.Col([
                dbc.Spinner(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id='event-manager-graph-container', children=[]),
                        ])
                    ], className="mb-3"),
                    color="primary",
                    type="border",
                ),
            ], width=8),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Div(id='event-manager-grid-container', children=[]),
            ], width=12),
        ]),
    ], fluid=True, className="p-0")
    return manager_layout

@callback(
    Output('event-manager-graph-container', 'children'),
    Output('event-manager-grid-container', 'children'),
    State('event-date-range-picker', 'start_date'),
    State('event-date-range-picker', 'end_date'),
    State('man-event-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('scale-toggle', 'value'),
    Input('manager-submit-button', 'n_clicks'),
    prevent_initial_callback=True
)
def render_event_manager_container(start_date, end_date, managers, events, scale, n_clicks):
    if not managers:
        return html.Div(), html.Div()
    if 'all' in managers:
        managers = None
    if n_clicks is None:
        return html.Div(), html.Div()
    df = fetch_driver_events_by_period_for_managers(start_date, end_date, managers)
    if df.empty:
        return dbc.Alert("No events found for the selected period and drivers.", color="warning"), html.Div()
    df = expand_events(df)
    df = df[(df['date'] >= pd.to_datetime(start_date).date()) & (df['date'] <= pd.to_datetime(end_date).date())]

    total_events_per_manager = df.groupby('manager')['id'].count().reset_index(name='total_events')
    event_counts_per_manager = df.groupby(['manager', 'event'])['id'].count().reset_index(name='count')
    merged_df = pd.merge(event_counts_per_manager, total_events_per_manager, on='manager')
    merged_df['proportion'] = (merged_df['count'] / merged_df['total_events']) * 100
    merged_df['proportion'] = merged_df['proportion'].apply(lambda x: round(x, 3))
    merged_df = merged_df.sort_values(by=scale, ascending=False)
    if events:
        merged_df = merged_df[merged_df['event'].isin(events)]
    pivot_df = merged_df.pivot(index='manager', columns='event', values=scale).reset_index().fillna(0)
    page_size = len(pivot_df)
    pivot_melted = pivot_df.melt(id_vars='manager', var_name='event', value_name=scale)
    scale_cap = scale.capitalize()
    fig = px.bar(pivot_melted, 
             x='manager', 
             y=scale, 
             color='event', 
             barmode='group',
             title=f'{scale_cap} of Each Event Type per Manager')
    fig.update_layout(showlegend=True)
    if scale == 'proportion':
        fig.update_layout(yaxis_tickformat='.1f%%')
        fig.update_layout(xaxis_tickangle=-45)
    else:
        fig.update_layout(yaxis_type="log")
    
    graph = dcc.Graph(figure=fig)
    grid = create_data_table('event-manager-table', pivot_df, 'event_manager_table.csv', page_size=page_size)
    
    return graph, grid



def create_driver_layout(min_date, max_date, event_options):
    driver_layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        create_date_range_picker('event-date-range-picker', min_date, max_date, populate_days_from_today=31),
                        create_dropdown('employee-dropdown', options=[], label='name', value='id', placeholder='Select driver', multi=True, add_all=False),
                        create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                        dbc.Row([
                            dbc.Col(dbc.RadioItems(
                                id='scale-toggle',
                                options=[
                                    {'label': 'Counts', 'value': 'count'},
                                    {'label': 'Proportional', 'value': 'proportion'}
                                ],
                                value='count',
                                inline=True
                            ), width=6),
                            dbc.Col(dbc.Button("Submit", id="driver-submit-button", color="primary"), width=6)
                        ], className="mt-3"),
                    ])
                ], className="mb-3"),
            ], width=4),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Spinner(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id='driver-event-graph-container', children=[])
                        ])
                    ], id='driver-event-graph-card', style={'display': 'none'}, className="mb-3"),
                    color="primary",
                    type="border",
                ),
            ], width=12),
        ]),
    ], fluid=True, className="p-0")
    return driver_layout
@callback(
    Output('driver-event-graph-container', 'children'),
    Output('driver-event-graph-card', 'style'),
    State('event-date-range-picker', 'start_date'),
    State('event-date-range-picker', 'end_date'),
    State('employee-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('scale-toggle', 'value'),
    Input('driver-submit-button', 'n_clicks'),
    prevent_initial_callback=True
)
def render_driver_event_container(start_date, end_date, drivers, events, scale, n_clicks):
    if not drivers or n_clicks is None:
        return [], {'display': 'none'}
    
    df = fetch_driver_events_by_period_for_drivers(start_date, end_date, drivers)
    if df.empty:
        return dbc.Alert("No events found for the selected period and drivers.", color="warning"), {'display': 'block'}
    
    if events:
        df = df[df['event'].isin(events)]
    
    df = expand_events(df)
    df = df[(df['date'] >= pd.to_datetime(start_date).date()) & (df['date'] <= pd.to_datetime(end_date).date())]

    color_map = px.colors.qualitative.Plotly
    event_colors = {event: color_map[i % len(color_map)] for i, event in enumerate(df['event'].unique())}
    
    driver_bars = []
    for driver in df['employee'].unique():
        driver_data = df[df['employee'] == driver]
        
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
            color_discrete_map=event_colors,
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
        driver_bars.append(dbc.Col(dcc.Graph(figure=global_bar_fig), width=6))
    
    return dbc.Row(driver_bars), {'display': 'block'}


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

@callback(
    Output("content", "className", allow_duplicate=True),
    Input("sidebar-state", "data"),
    prevent_initial_call=True
)
def adjust_content(sidebar_state):
    if sidebar_state == "closed":
        return "mt-3 px-3 content-expanded"
    return "mt-3 px-3"