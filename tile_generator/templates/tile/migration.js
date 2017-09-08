exports.migrate = function(properties) {
	{% if migration %}
	{{ migration | render | indent(2,false) }}
	{% endif %}
	return properties;
};
