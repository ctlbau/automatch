import dash
from dash import html, callback, Input, Output, State, callback_context, dcc, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from db.db_support import fetch_drivers_matches, unmatch_drivers, match_drivers_to_vehicle, fetch_vehicle_plates
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
                ),
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
        *matched_drivers_cards,
    ], style={'width': '33%', 'margin-bottom': '20px'})

    return component_structure

unmatch_confirmation_dialog = dbc.Modal(
    [
        dbc.ModalBody("Are you sure you want to unmatch this driver?"),
        dbc.ModalFooter(
            [
                dbc.Button("Cancel", id="cancel-unmatch", className="ml-auto"),
                dbc.Button("Unmatch", id="confirm-unmatch", className="ml-auto", color="danger"),
            ]
        ),
    ],
    id="unmatch-confirmation-dialog",
    is_open=False,
)

match_confirmation_dialog = dbc.Modal(
    [
        dbc.ModalBody("Are you sure you want to match these drivers?"),
        dbc.ModalFooter(
            [
                dbc.Button("Cancel", id="cancel-match", className="ml-auto"),
                dbc.Button("Match", id="confirm-match", className="ml-auto", color="success"),
            ]
        ),
    ],
    id="match-confirmation-dialog",
    is_open=False,
)

# Match button
match_button = dbc.Button(
        "Match",
        id="match-button",
        className="mb-3",
        color="success",
        n_clicks=0,
        disabled=True,  # Initially disabled
    )

# Dropdown for selecting vehicle plates
vehicle_plate_dropdown = dcc.Dropdown(
    id='vehicle-plate-dropdown',
    options=[{'label': plate, 'value': plate} for plate in fetch_vehicle_plates()],
    placeholder="Select a vehicle plate",
    clearable=False,
    style={'width': '100%'},  # Set the width of the dropdown to be wider
)

# Toast notification for successful match
match_success_toast = dbc.Toast(
    id="match-toast",
    header="Match Successful",
    is_open=False,
    dismissable=True,
    icon="success",
    duration=10000,
    style={"position": "fixed", "top": 10, "right": 10, "width": 350},
)

# Layout
layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.Div(vehicle_plate_dropdown, id="vehicle-plate-dropdown-container", style={'display': 'inline-block', 'marginRight': '10px', 'width': '300px'}, className="d-flex justify-content-center"),
        html.Div(match_button, id="match-button-container", style={'display': 'inline-block'}, className="d-flex justify-content-center"),
        match_success_toast,
    ], className="d-flex justify-content-center", style={'marginBottom': '10px'}),
    html.Div(id='collapse-container', children=[], className="d-flex flex-wrap justify-content-center"),  # Added classes for centering and wrapping
    dcc.Store(id='url-candidates-store'),  # Store for candidates data
    dcc.Store(id='clicked-unmatch-button-store'),
    unmatch_confirmation_dialog,
    match_confirmation_dialog,
      # Include the toast notification in the layout
])


@callback(Output('collapse-container', 'children'), 
          [Input('url-candidates-store', 'modified_timestamp')],
          [State('url-candidates-store', 'data')])
def display_candidates(ts, data_store):
    if data_store is None:
        raise PreventUpdate
    data_dict = json.loads(data_store)
    matches = data_dict.get("matches", [])
    matches = fetch_drivers_matches([match["id"] for match in matches])
    return [create_candidate_component(match) for match in matches]


@callback(
    Output('unmatch-confirmation-dialog', 'is_open'),
    Output('url-candidates-store', 'data', allow_duplicate=True),
    Output('clicked-unmatch-button-store', 'data'),
    # Output('match-toast', 'is_open', allow_duplicate=True),  # Added output for the toast notification
    # Output('match-toast', 'children', allow_duplicate=True),  # Added output for the toast notification content
    [Input({'type': 'unmatch-button', 'candidate_id': ALL, 'driver_id': ALL}, 'n_clicks'), # Card unmatch buttons
     Input('confirm-unmatch', 'n_clicks'), # Dialog Confirm unmatch button
     Input('cancel-unmatch', 'n_clicks')], # Dialog Cancel unmatch button
    [State('unmatch-confirmation-dialog', 'is_open'),
     State({'type': 'unmatch-button', 'candidate_id': ALL, 'driver_id': ALL}, 'id'),
     State('url-candidates-store', 'data'),
     State('clicked-unmatch-button-store', 'data')],  # Add this state
     prevent_initial_call=True
)
def handle_unmatch(unmatch_clicks, confirm_click, cancel_click, is_open, button_id, data_store, clicked_unmatch_button):
    if not button_id or not any(unmatch_clicks):
        raise PreventUpdate
    ctx = callback_context

    # Determine which button was clicked
    button_clicked = ctx.triggered[0]['prop_id'].split('.')[0]

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
        # Perform the unmatch operation
        unmatch_drivers(candidate_id, driver_id)
        # Update the data store with with new ts to trigger the display_candidates callback
        data_dict = json.loads(data_store)
        matches = data_dict.get("matches", [])
        # Close the dialog and force page refresh components to reflect the unmatch
        return False, json.dumps(add_metadata_to_data(matches)), dash.no_update
    elif 'cancel-unmatch' in button_clicked and is_open:
        # Just close the dialog without doing anything
        return False, dash.no_update, dash.no_update  # No update to the store
    else:
        raise PreventUpdate

@callback(
    Output('match-button', 'disabled'),
    [Input('vehicle-plate-dropdown', 'value')]
)
def toggle_match_button_state(selected_plate):
    return selected_plate is None

@callback(
    Output('match-confirmation-dialog', 'is_open'),
    Output('url-candidates-store', 'data', allow_duplicate=True),
    Output('match-toast', 'is_open'),  # Added output for the toast notification
    Output('match-toast', 'children'),  # Added output for the toast notification content
    [Input('match-button', 'n_clicks'), # Match button
     Input('confirm-match', 'n_clicks'), # Dialog Confirm match button
     Input('cancel-match', 'n_clicks')], # Dialog Cancel match button
    [State('match-confirmation-dialog', 'is_open'),
     State('url-candidates-store', 'data'),
     State('vehicle-plate-dropdown', 'value')],  # Add this state for selected vehicle plate
     prevent_initial_call=True
)
def handle_match(match_click, confirm_click, cancel_click, is_open, data_store, selected_plate):
    if not any([match_click, confirm_click, cancel_click]):
        raise PreventUpdate
    ctx = callback_context

    # Determine which button was clicked
    button_clicked = ctx.triggered[0]['prop_id'].split('.')[0]

    if 'match-button' in button_clicked and selected_plate:
        # Open the dialog
        return True, dash.no_update, dash.no_update, dash.no_update  # Adjusted for the correct number of outputs
    elif 'confirm-match' in button_clicked and is_open:
        # Perform the match operation
        data_dict = json.loads(data_store)
        matches = data_dict.get("matches", [])
        driver_ids = [match["id"] for match in matches]
        match_drivers_to_vehicle(driver_ids, selected_plate)
        # Update the data store with new ts to trigger the display_candidates callback
        # Close the dialog and force page refresh components to reflect the match
        matched_drivers_names = [match["name"] for match in matches]
        matched_info = f"Matched drivers: {', '.join(matched_drivers_names)} to vehicle {selected_plate}"
        # Show the toast notification with the matched information
        return False, json.dumps(add_metadata_to_data(matches)), True, matched_info
    elif 'cancel-match' in button_clicked and is_open:
        # Just close the dialog without doing anything
        return False, dash.no_update, dash.no_update, dash.no_update  # Adjusted for the correct number of outputs
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
        "last_updated": datetime.now().isoformat()
    }
