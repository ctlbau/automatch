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

    return html.Div([  # This div wraps each button-collapse pair
        html.Div([
            dbc.Button(
                candidate["name"],
                id=button_id,
                className="mb-3",
                color="secondary",
                n_clicks=0
            ),
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody(
                        [dbc.Card(
                            dbc.CardBody([  
                                html.H5(matched_driver["name"], className="card-title"),
                                html.P("Manager: " + (matched_driver["manager"] if matched_driver["manager"] is not None else "Not assigned")),
                                html.P("Shift: " + (matched_driver["shift"] if matched_driver["shift"] is not None else "Not assigned")),
                                html.P("Vehicle: " + matched_driver["vehicle"])
                            ], style={'margin': '10px'})  # Added margin for separation
                        ) for matched_driver in candidate["matched_drivers"]],
                        style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'start', 'margin': '10px'}  # Adjusted for side by side display with wrap and margin for separation
                    ),
                    style={'width': '100%'}  # This ensures the card itself does not exceed the width of the button
                ),
                id=collapse_id,
                is_open=False,
            ),
        ], style={'margin-right': '20px', 'flex': '1 1 0', 'display': 'flex', 'flex-direction': 'column'}),  # This styles each pair as a column
    ], style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'start'}  # This styles the overall container
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
