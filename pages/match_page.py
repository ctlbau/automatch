import dash
from dash import html, callback, Input, Output, State, callback_context, dcc, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from db.db_support import fetch_drivers_matches, unmatch_drivers
import json
import base64  # Added for decoding URL parameter
from urllib.parse import parse_qs, urlparse  # Added for parsing URL
from dash.exceptions import PreventUpdate
from datetime import datetime

dash.register_page(__name__, path='/match_page')

# Update the url-candidates-store with the matches for the drivers in the URL
@callback(Output('url-candidates-store', 'data'), [Input('url', 'search')])
def update_candidates_store(search):
    parsed_search = parse_qs(search.lstrip('?'))
    driver_ids_encoded = parsed_search.get('drivers', [None])[0]
    if driver_ids_encoded:
        driver_ids_decoded = base64.urlsafe_b64decode(driver_ids_encoded.encode()).decode()
        driver_ids_decoded = json.loads(driver_ids_decoded)
        matches = fetch_drivers_matches(driver_ids_decoded)
        data_with_metadata = add_metadata_to_data(matches)
        return json.dumps(data_with_metadata)
    return dash.no_update


# Function to create a button and collapse component for each candidate
def create_candidate_component(candidate):
    button_id = {"type": "collapse-button", "index": candidate['id']}
    collapse_id = {"type": "collapse", "index": candidate['id']}

    # Button for the candidate
    candidate_modal_button = dbc.Button(
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
            html.P("ID: " + str(int(candidate["id"]))),
            html.P("Manager: " + (candidate["manager"] if candidate["manager"] is not None else "Not assigned")),
            html.P("Shift: " + (candidate["shift"] if candidate["shift"] is not None else "Not assigned")),
            # dbc.Button(
            #     "Unmatch All",
            #     id={"type": "unmatch-all-button", "candidate_id": candidate['id']},
            #     className="mt-2",
            #     color="danger",
            #     n_clicks=0
            # )
        ], style={'margin': '10px'})
    )

    # Cards for each matched driver
    matched_drivers_cards = [
        dbc.Card(
            dbc.CardBody([
                html.H5(matched_driver["name"], className="card-title"),
                html.P("ID: " + str(int(matched_driver["id"]))),
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
        candidate_modal_button,
        candidate_collapse,
        *matched_drivers_cards
    ], style={'width': '33%', 'margin-bottom': '20px'})

    return component_structure

confirmation_dialog = dbc.Modal(
    [
        dbc.ModalBody("Are you sure you want to unmatch this driver?"),
        dbc.ModalFooter(
            [
                dbc.Button("Cancel", id="cancel-unmatch", className="ml-auto"),
                dbc.Button("Unmatch", id="confirm-unmatch", className="ml-auto", color="danger"),
            ]
        ),
    ],
    id="confirmation-dialog",
    is_open=False,
)

# Layout
layout = html.Div([
    dcc.Location(id='url', refresh=False),
    # html.Div(id='data-display-page', children=[]),  # Added a div to display the data
    html.Div(id='collapse-container', children=[], className="d-flex flex-wrap justify-content-center"),  # Added classes for centering and wrapping
    dcc.Store(id='url-candidates-store'),  # Store for candidates data
    dcc.Store(id='clicked-unmatch-button-store'),
    confirmation_dialog
])

# @callback(
#     Output('data-display-page', 'children'),  # Target the dcc.Location component
#     [Input('clicked-unmatch-button-store', 'data')],
#     # prevent_initial_call=True  # Prevent navigation on initial load
# )
# def display_data(data):
#     if data:
#         return data
#     return "No data to display."


@callback(Output('collapse-container', 'children'), 
          [Input('url-candidates-store', 'modified_timestamp')],
          [State('url-candidates-store', 'data')])
def display_candidates(ts, data_store):
    if data_store is None:
        raise PreventUpdate
    data_dict = json.loads(data_store)
    matches = data_dict.get("matches", [])
    return [create_candidate_component(match) for match in matches]


@callback(
    Output('confirmation-dialog', 'is_open'),
    Output('url-candidates-store', 'data', allow_duplicate=True),
    Output('clicked-unmatch-button-store', 'data'),  # Add this output
    [Input({'type': 'unmatch-button', 'candidate_id': ALL, 'driver_id': ALL}, 'n_clicks'), # Card unmatch buttons
     Input('confirm-unmatch', 'n_clicks'), # Dialog Confirm unmatch button
     Input('cancel-unmatch', 'n_clicks')], # Dialog Cancel unmatch button
    [State('confirmation-dialog', 'is_open'),
     State({'type': 'unmatch-button', 'candidate_id': ALL, 'driver_id': ALL}, 'id'),
     State('url-candidates-store', 'data'),
     State('clicked-unmatch-button-store', 'data')],  # Add this state
     prevent_initial_call=True
)
def handle_dialog_and_unmatch(unmatch_clicks, confirm_click, cancel_click, is_open, button_id, data_store, clicked_unmatch_button):
    if not button_id or not any(unmatch_clicks):
        raise PreventUpdate
    ctx = callback_context

    # Determine which button was clicked
    button_clicked = ctx.triggered[0]['prop_id'].split('.')[0]
    print("Button clicked:", button_clicked)

    if 'unmatch-button' in button_clicked:
        # Open the dialog
        # Store the clicked unmatch-button id
        button_info = json.loads(button_clicked)
        candidate_id = button_info['candidate_id']
        driver_id = button_info['driver_id']
        # Store these IDs in clicked-unmatch-button-store
        ids_to_store = json.dumps({'candidate_id': candidate_id, 'driver_id': driver_id})
        return True, dash.no_update, ids_to_store
    elif 'confirm-unmatch' in button_clicked and is_open:
        clicked_unmatch_button = json.loads(clicked_unmatch_button)
        if not clicked_unmatch_button:
            raise PreventUpdate
        candidate_id = clicked_unmatch_button['candidate_id']
        driver_id = clicked_unmatch_button['driver_id']
        print("Candidate id:", candidate_id)
        print("Driver id:", driver_id)
        # Perform the unmatch operation
        unmatch_drivers(candidate_id, driver_id)
        data_dict = json.loads(data_store)
        matches = data_dict.get("matches", [])
        # Close the dialog and force page refresh components to reflect the unmatch
        return False, json.dumps(add_metadata_to_data(matches)), dash.no_update  # No update to the store
    elif 'cancel-unmatch' in button_clicked and is_open:
        # Just close the dialog without doing anything
        return False, dash.no_update, dash.no_update  # No update to the store
    else:
        raise PreventUpdate

@callback(
    Output({'type': 'collapse', 'index': MATCH}, 'is_open'),
    [Input({'type': 'collapse-button', 'index': MATCH}, 'n_clicks')],
    [State({'type': 'collapse', 'index': MATCH}, 'is_open')]
)
def toggle_collapse(n, is_open):
    if n is None or n == 0:
        raise PreventUpdate
    return not is_open

def add_metadata_to_data(data):
    return {
        "matches": data,
        "last_updated": datetime.now().isoformat()  # Use the current timestamp as metadata
    }