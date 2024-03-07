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
    return html.Div([
        dbc.Button(
            candidate["name"],
            id={"type": "collapse-button", "index": candidate['id']},  # Updated ID format
            className="mb-3",
            color="primary",
            n_clicks=0,
        ),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([html.P(driver["name"]) for driver in candidate["matched_drivers"]])),
            id={"type": "collapse", "index": candidate['id']},  # Updated ID format
            is_open=False,
        ),
    ])


# Layout
layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='collapse-container', children=[]),
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




# @callback(
#     [Output(f"collapse-{i}", "is_open") for i in range(10)],  # Assuming a maximum of 10 candidates
#     [Input(f"collapse-button-{i}", "n_clicks") for i in range(10)],
#     [State(f"collapse-{i}", "is_open") for i in range(10)] + [State('candidate-store', 'data')]
# )
# def toggle_collapse(*args):
#     ctx = callback_context
#     store_data = args[-1]  # Last argument is the store data
#     candidates = json.loads(store_data) if store_data else []
#     args = args[:-1]  # The rest are the callback arguments

#     if not ctx.triggered:
#         return [False for _ in range(10)]
#     else:
#         button_id = ctx.triggered[0]["prop_id"].split(".")[0]
#         candidate_id = int(button_id.split("-")[-1])
#         return [not args[i] if candidate['id'] == candidate_id else args[i] for i, candidate in enumerate(candidates)]
