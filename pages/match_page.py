import dash
from dash import html, callback, Input, Output, State, callback_context, dcc, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from db.db_support import fetch_drivers_matches
import json
import base64  # Added for decoding URL parameter
from urllib.parse import parse_qs, urlparse  # Added for parsing URL

dash.register_page(__name__, path='/match_page')

# Function to create a button and collapse component for each candidate
def create_candidate_component(candidate):
    button_id = {"type": "collapse-button", "index": candidate['id']}
    collapse_id = {"type": "collapse", "index": candidate['id']}

    return html.Div([
        dbc.Button(
            candidate["name"],
            id=button_id,
            className="mb-3",
            color="secondary",
            n_clicks=0,
            style={'width': '100%'}  # Ensure the button takes full width of its container
        ),
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody(
                    [html.P("Matched with: " + driver["name"] + " with shift " + driver["shift"] + ". " + "They share vehicle: " + driver["vehicle"],
                            style={'white-space': 'normal', 'overflow-x': 'auto', 'word-wrap': 'break-word'}) 
                     for driver in candidate["matched_drivers"]],
                    style={'max-width': '100%'}  # This applies a maximum width of 100% to the card body
                ),
                style={'width': '100%'}  # This ensures the card itself does not exceed the width of the button
            ),
            id=collapse_id,
            is_open=False,
        ),
    ], style={'width': '100%'}  # This ensures the containing div also takes full width
)


# Layout
layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='collapse-container', children=[], className="d-flex flex-wrap justify-content-center"),  # Added classes for centering and wrapping
    html.Div(id="data-display"),  # Element to display the data
    dcc.Store(id='candidate-store')  # Store for candidates data
])

@callback(Output('candidate-store', 'data'), [Input('url', 'search')])
def update_candidates_store(search):
    parsed_search = parse_qs(search.lstrip('?'))
    driver_ids_encoded = parsed_search.get('drivers', [None])[0]
    if driver_ids_encoded:
        driver_ids_decoded = base64.urlsafe_b64decode(driver_ids_encoded.encode()).decode()
        driver_ids_decoded = json.loads(driver_ids_decoded)
        matches = fetch_drivers_matches(driver_ids_decoded)
        return json.dumps(matches)
    return dash.no_update


@callback(Output('collapse-container', 'children'), [Input('candidate-store', 'data')])
def display_candidates(data):
    if data:
        matches = json.loads(data)
        return [create_candidate_component(match) for match in matches]
    return []


@callback(
    Output({'type': 'collapse', 'index': MATCH}, 'is_open'),
    [Input({'type': 'collapse-button', 'index': MATCH}, 'n_clicks')],
    [State({'type': 'collapse', 'index': MATCH}, 'is_open')]
)
def toggle_collapse(n, is_open):
    if n is None or n == 0:
        raise PreventUpdate  # Correctly raising PreventUpdate here
    return not is_open
