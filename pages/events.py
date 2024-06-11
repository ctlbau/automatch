import dash
from dash import callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db.events import fetch_managers, get_min_max_dates_from_schedule_events, fetch_driver_events_by_period, fetch_event_options
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
                    create_dropdown('manager-dropdown', options=manager_options, label='name', value='name', placeholder='Select manager', multi=False, add_all=False),
                    create_dropdown('event-dropdown', options=event_options, label='name', value='name', placeholder='Select event', multi=True, add_all=False),
                    dcc.Loading(html.Div(id='manager-event-container', children=[], style={'width': '100%'}), type='circle'),
                ])
            ])
        ])
        return manager_layout
    elif tab == 'driver-event-tab':
        return "Driver View"
    
@callback(
    Output('manager-event-container', 'children'),
    Input('event-date-range-picker', 'start_date'),
    Input('event-date-range-picker', 'end_date'),
    Input('manager-dropdown', 'value'),
    Input('event-dropdown', 'value'),
    prevent_initial_callback=True
)
def render_manager_event_container(start_date, end_date, manager, events):
    if not manager:
        return html.Div()
    df = fetch_driver_events_by_period(start_date, end_date, manager)
    df = expand_events(df)
    df['week'] = df['date'].dt.isocalendar().week
    df = df[(df['start'] >= start_date) & (df['end'] <= end_date)]
    start_week = df['week'].min()
    end_week = df['week'].max()
    df = df[df['manager'] == manager]
    if events:
        df = df[df['event'].isin(events)]
    dfg = df.groupby(['week', 'event']).agg({'event': 'count'}).rename(columns={'event': 'event_count'})
    dfg.reset_index(inplace=True)
    pivot = dfg.pivot(index=['event'], columns=['week'], values='event_count').fillna(0)
    pivot = pivot.reset_index()
    pivot = pivot.sort_values(by=['event'])
    
    numeric_cols = pivot.select_dtypes(include='number').columns
    pivot['Total'] = pivot[numeric_cols].sum(axis=1)
    
    table = create_data_table('events-table', pivot, 'events.csv')
    line_fig = px.line(
        dfg,
        x='week',
        y='event_count',
        color='event',
        title=f'Event Count from week {start_week} to {end_week} for {manager}'
    )

    line_fig.update_layout(
        xaxis_title="Week",
        yaxis_title="Event Count",
        yaxis_type="log",
        xaxis_tickangle=-45
    )

    pie_fig = px.pie(
        dfg,
        values='event_count',
        names='event'
    )

    return [dcc.Graph(figure=line_fig), dcc.Graph(figure=pie_fig), table]