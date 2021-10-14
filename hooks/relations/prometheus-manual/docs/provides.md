# <a id="prometheusmanualprovides"></a>`class PrometheusManualProvides(RequesterEndpoint)`

Base class for Endpoints that create requests in the request / response
pattern.

Subclasses **must** set the ``REQUEST_CLASS`` attribute to a subclass
of :class:`BaseRequest` which defines the fields the request will use.

## <a id="prometheusmanualprovides-all_departed_units"></a>`all_departed_units`

Collection of all units that were previously part of any relation on
this endpoint but which have since departed.

This collection is persistent and mutable.  The departed units will
be kept until they are explicitly removed, to allow for reasonable
cleanup of units that have left.

Example: You need to run a command each time a unit departs the relation.

.. code-block:: python

    @when('endpoint.{endpoint_name}.departed')
    def handle_departed_unit(self):
        for name, unit in self.all_departed_units.items():
            # run the command to remove `unit` from the cluster
            #  ..
        self.all_departed_units.clear()
        clear_flag(self.expand_name('departed'))

Once a unit is departed, it will no longer show up in
:attr:`all_joined_units`.  Note that units are considered departed as
soon as the departed hook is entered, which differs slightly from how
the Juju primitives behave (departing units are still returned from
``related-units`` until after the departed hook is complete).

This collection is a :class:`KeyList`, so can be used as a mapping to
look up units by their unit name, or iterated or accessed by index.

## <a id="prometheusmanualprovides-all_joined_units"></a>`all_joined_units`

A list view of all the units of all relations attached to this
:class:`~charms.reactive.endpoints.Endpoint`.

This is actually a
:class:`~charms.reactive.endpoints.CombinedUnitsView`, so the units
will be in order by relation ID and then unit name, and you can access a
merged view of all the units' data as a single mapping.  You should be
very careful when using the merged data collections, however, and
consider carefully what will happen when the endpoint has multiple
relations and multiple remote units on each.  It is probably better to
iterate over each unit and handle its data individually.  See
:class:`~charms.reactive.endpoints.CombinedUnitsView` for an
explanation of how the merged data collections work.

Note that, because a given application might be related multiple times
on a given endpoint, units may show up in this collection more than
once.

## <a id="prometheusmanualprovides-all_units"></a>`all_units`

.. deprecated:: 0.6.1
   Use :attr:`all_joined_units` instead

## <a id="prometheusmanualprovides-endpoint_name"></a>`endpoint_name`

Relation name of this endpoint.

## <a id="prometheusmanualprovides-is_joined"></a>`is_joined`

Whether this endpoint has remote applications attached to it.

## <a id="prometheusmanualprovides-joined"></a>`joined`

.. deprecated:: 0.6.3
   Use :attr:`is_joined` instead

## <a id="prometheusmanualprovides-manage_flags"></a>`def manage_flags(self)`

Method that subclasses can override to perform any flag management
needed during startup.

This will be called automatically after the framework-managed automatic
flags have been updated.

## <a id="prometheusmanualprovides-register_job"></a>`def register_job(self, job_name, job_data, ca_cert=None)`

Register a manual job.

The job data should be the (unserialized) data defining the job.

To ensure uniqueness, a UUID will be added to the job name, and it will
be injected into the job data.

If a CA cert is given, the value of any ca_file field in the job data
will be replaced with a filename after the CA cert data is written, so
a placeholder value should be used.

## <a id="prometheusmanualprovides-relations"></a>`relations`

Collection of :class:`Relation` instances that are established for
this :class:`Endpoint`.

This is a :class:`KeyList`, so it can be iterated and indexed as a list,
or you can look up relations by their ID.  For example::

    rel0 = endpoint.relations[0]
    assert rel0 is endpoint.relations[rel0.relation_id]
    assert all(rel is endpoint.relations[rel.relation_id]
               for rel in endpoint.relations)
    print(', '.join(endpoint.relations.keys()))

## <a id="prometheusmanualprovides-requests"></a>`requests`

A list of all requests which have been submitted.

## <a id="prometheusmanualprovides-responses"></a>`responses`

A list of all responses which have been received.
