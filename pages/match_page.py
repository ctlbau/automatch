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

    # Button for the candidate
    candidate_button = dbc.Button(
        candidate["name"],
        id=button_id,
        className="mb-3",
        color="secondary",
        n_clicks=0
    )
    # Card for candidate
    candidate_card = dbc.Card(
        dbc.CardBody([
            html.H5(candidate["name"], className="card-title"),
            html.P("ID: " + str(candidate["id"])),
            html.P("Manager: " + (candidate["manager"] if candidate["manager"] is not None else "Not assigned")),
            html.P("Shift: " + (candidate["shift"] if candidate["shift"] is not None else "Not assigned")),
            dbc.Button(
                "Unmatch All",
                id={"type": "unmatch-all-button", "candidate_id": candidate['id']},
                className="mt-2",
                color="danger",
                n_clicks=0
            )
        ], style={'margin': '10px'})
    )

    # Cards for each matched driver
    matched_drivers_cards = [
        dbc.Card(
            dbc.CardBody([
                html.H5(matched_driver["name"], className="card-title"),
                html.P("ID: " + str(matched_driver["id"])),
                html.P("Manager: " + (matched_driver["manager"] if matched_driver["manager"] is not None else "Not assigned")),
                html.P("Shift: " + (matched_driver["shift"] if matched_driver["shift"] is not None else "Not assigned")),
                html.P("Vehicle: " + matched_driver["vehicle"]),
                dbc.Button(
                    "Unmatch",
                    id={"type": "unmatch-button", "candidate_id": candidate['id'], "driver_id": matched_driver['id']},
                    className="mt-2",
                    color="warning",
                    n_clicks=0
                )
            ], style={'margin': '10px'})
        ) for matched_driver in candidate["matched_drivers"]
    ]

    # Collapse component that toggles the visibility of the candidate card
    candidate_collapse = dbc.Collapse(
        dbc.Card(candidate_card, className="mb-2"),
        id=collapse_id,
        is_open=False,
    )

    # Wrapping the button and collapse component together
    component_structure = html.Div([
        candidate_button,
        candidate_collapse,
        *matched_drivers_cards
    ], style={'width': '33%', 'margin-bottom': '20px'})

    return component_structure




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
