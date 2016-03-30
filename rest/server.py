#!/usr/bin/python3

#
# IMPORTS
#
from tessia_baselib.hypervisors import Hypervisor
from tessia_baselib.guests import Guest

import flask

#
# CONSTANTS AND DEFINITIONS
#
app = flask.Flask(__name__)

#
# CODE
#

# definition of each entry point
@app.route(
    '/hypervisors/<system_name>/guests/<guest_name>/start',
    methods=['PUT'])
def startGuest(hyp_name, guest_name):
    """
    Implements the start guest action.

    Args:
        hyp_name: name identifier for hypervisor system
        guest_name: name of guest as known by hypervisor

    Returns:
        TODO

    Raises:
        TODO
    """
    # get parsed json data, in case of error raises BadRequest exception
    request_data = flask.request.get_json(force=True)

    # Create the object according to type specified. If request is malformed
    # a KeyRrror will occur and we return a error response.
    try:
        resources = request_data['guest']['resources']
        boot_method = request_data['guest']['boot']['method']
        boot_device = request_data['guest']['boot']['device']
        guest_ext = request_data['extensions'].get('guest', {})

        # TODO: apply sanity check on values
        hypervisorObj = Hypervisor(
            hyp_type=request_data['hypervisor']['type'],
            logger=None,
            system_name=request_data['hypervisor']['username'],
            host_name=request_data['hypervisor']['hostname'],
            user=request_data['hypervisor']['username'],
            passwd=request_data['hypervisor']['password'],
            extensions=request_data['extensions']['hypervisor'],
        )
    # user passed missing content
    except KeyError as excObj:
        msg = 'Missing key: {}'.format(str(excObj))
        response = flask.make_response(msg, 400)
        return response
    # user passed some invalid option (like unsupported type)
    except RuntimeError as excObj:
        response = flask.make_response(str(excObj), 400)
        return response
    # unexpected error: report as server error
    except BaseException as excObj:
        response = flask.make_response(str(excObj), 500)
        return response

    # login to hypervisor
    msg = hypervisorObj.login()
    # for now we just assume user passed invalid credentials: report as
    # client error
    if msg != 'ok':
        response = flask.make_response(msg, 400)
        return response

    # start the guest
    msg = hypervisorObj.start(guest_name, resources, boot_method, boot_device,
                              guest_ext)
    # action failed: report as Bad gateway error
    if msg != 'ok':
        response = flask.make_response(msg, 502)
        return response

    # TODO: implement async task queue and return task id
    return flask.jsonify(result='ok', message='', taskid=None)
# startGuest()

if __name__ == "__main__":
    app.run()
