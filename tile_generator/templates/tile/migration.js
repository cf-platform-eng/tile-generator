exports.migrate = function(properties) {
	{% if migration %}
	{{ migration | render }}
	{% endif %}
	return properties;
};
