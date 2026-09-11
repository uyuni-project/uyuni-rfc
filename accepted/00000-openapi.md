## Feature Name: OpenAPI Adoption for Describing Uyuni HTTP API
**Start Date:** 13/12/2024

### Summary
Introduce the OpenAPI specification to describe and document Uyuni's HTTP API, replacing the existing static documentation. It aims to enhance user and developer experiences by providing interactive, standardized, and more accessible API documentation.

### Motivation
The adoption of OpenAPI aims to enhance both user and developer experiences by modernizing API documentation, making it more accessible, interactive, and aligned with industry standards. The current static API documentation lacks interactivity, making it difficult for users to explore and use API endpoints effectively. Integrating OpenAPI-generated interactive documentation, such as Swagger UI, directly into Uyuni’s Web UI allows users to explore, experiment with, and test API endpoints in real-time. This eliminates the need for additional programming effort and helps users achieve their goals more efficiently.

OpenAPI is a widely recognized standard supported by a robust ecosystem of tools, including API validators, client generators, and testing frameworks. Transitioning to OpenAPI enables developers and users to leverage these tools, streamlining workflows and boosting productivity. Additionally, OpenAPI annotations integrate seamlessly with Java’s syntax and provide strong typing, reducing errors and simplifying maintenance compared to the current Javadoc-based approach, which relies on non-standard tags. This shift ensures consistent, standardized documentation while minimizing the effort required to maintain it.

The expected outcome of this integration is to deliver Uyuni's API documentation as a valid OpenAPI JSON specification, complemented by an interactive Swagger UI integrated into Uyuni’s web interface, allowing users to explore and experiment with the API.


### Detailed Design

#### A. Describing the API
Endpoints will be described using Swagger annotations, replacing the current Javadoc comments. Each API method will be annotated with Swagger elements such as `@Operation`, `@Parameter`, `@ApiResponse`, and `@Schema` to define essential details, including summaries, parameters, request bodies, and responses. For example:

**Current documentation:**
```
    /*
 	* @apidoc.doc Update Content Environment with given label
 	* @apidoc.param #param_desc("string", "projectLabel", "Content Project label")
 	* @apidoc.param #param_desc("string", "envLabel", "Content Environment label")
 	* @apidoc.param
 	*  #struct_begin("props")
 	*  	#prop_desc("string", "name", "Content Environment name")
 	*  	#prop_desc("string", "description", "Content Environment description")
 	*  #struct_end()
 	* @apidoc.returntype $ContentEnvironmentSerializer
 	*/
```

**Proposed Swagger Documentation:**
```
    @Operation(
        summary = "Update Content Environment",
        tags = {"contentmanagement"},
        description = "Update Content Environment with given label",
        responses = {
            @ApiResponse(
                responseCode = "200", description = "Successful response",
                content = @Content(
                    mediaType = "application/json",
                    schema = @Schema(
                        type = "object",
                        properties = {
                            @StringToClassMapItem(key = "label", value = String.class),
                            @StringToClassMapItem(key = "name", value = String.class),
                            @StringToClassMapItem(key = "description", value = String.class)
                        }
                    )
                )
	        )
	    },
	    parameters = {
            @Parameter(
                name="projectLabel",
                schema = @Schema(type = "string"),
                required = true,
                description = "Content Project label",
                in = ParameterIn.QUERY
            ),
            @Parameter(cr
                name="envLabel",
                schema = @Schema(type = "string"),
                required = true,
                description = "Environment label",
                in = ParameterIn.QUERY
            )
	    },
        requestBody = @RequestBody(
            description = "Request body description",
            content = @Content(
                mediaType = "application/json",
                schema = @Schema(
                    type = "object",
                    properties = {
                        @StringToClassMapItem(key = "name", value = String.class),
                        @StringToClassMapItem(key = "description", value = String.class)
                    }
                )
            )
        )
	)

```

##### A.1. Library Dependencies
Two additional Maven dependencies will be added to Uyuni to support Swagger annotations:
 - `io.swagger.core.v3.swagger-core and`
 - `io.swagger.core.v3.swagger-annotations`

##### A.2. Existing API Endpoints
To facilitate the transition, a one-time scanner tool will be developed to automate the conversion of existing Javadoc-based documentation into Swagger annotations. This tool will be implemented as a Java Doclet that systematically scans the codebase to identify predefined patterns in the Javadoc comments. Once identified, the tool will annotate the corresponding methods with the appropriate `@Operation` annotations.

Additionally, the scanner will detect the use of API serializers that describe the return types of endpoints. It will parse the associated Javadoc comments of these serializers to extract the necessary details and incorporate them into the `@Operation` definitions.

##### A.3. XML-RPC API code examples

For XML-RPC endpoints, it is possible to provide a specific section in the web UI containing sample scripts. In addition to this, the `description` and `examples` fields of Swagger operation documentation can be used to aid understanding.

##### A.4. Describing the Request Body

Currently, the request body of an API endpoint is typically mapped to a method parameter of type `java.util.Map<String, Object>`, where the keys represent parameter names. The structure of these parameters is documented in Javadocs using a custom format. For example:

```
     * @apidoc.param
 	*  #struct_begin("props")
 	*  	#prop_desc("string", "name", "Content Environment name")
 	*  	#prop_desc("string", "description", "Content Environment description")
 	*  #struct_end()
```

To improve the description of the request body, one option is to define a Data Transfer Object (DTO) class and annotate it with Swagger annotations. This approach ensures that an equivalent model is reflected in the API specification.

However, for endpoints where the request body is already defined as a `java.util.Map`, it is possible to define an anonymous model in the specification using the `@StringToClass` annotation. For example:

```
schema = @Schema(
    type = "object",
    properties = {
        @StringToClassMapItem(key = "label", value = String.class),
        @StringToClassMapItem(key = "name", value = String.class),
        @StringToClassMapItem(key = "description", value = String.class)
    }
)

```

For migrating the documentation of existing endpoints, this approach—defining the request body as an anonymous model—will be used.

##### A.5. Describing the Response

Currently, the return values of API endpoints are typically serialized using instances of `com.suse.manager.api.ApiResponseSerializer`. In this process, the endpoint method returns a specific entity, which is then converted into a `com.suse.manager.api.SerializedApiResponse`. This serialized response is mapped to a `java.util.Map<String, Object>`` containing properties that represent the JSON object returned to the user.

In the same way as the request body, to achieve seamless Swagger integration, transitioning to Data Transfer Objects (DTOs) for response representation would be ideal. However, for the existing endpoints, it is feasible to define an anonymous model in the specification using the `@StringToClass` annotation. This approach will be adopted during the migration of the current documentation.

Additionally, when an endpoint is described using Swagger, its return type is automatically converted into a model within the specification. To prevent exposing excessive details about internal entities, a condition will be implemented to exclude the method's return type from the specification if a serializer class is present in the endpoint definitions. This ensures controlled and secure exposure of the API's return data.

#### B. Generating the Specification

Once all the API endpoints have been described using Swagger annotations, it is necessary to have an implementation of `io.swagger.v3.oas.integration.api.OpenApiReader` for parsing the annotations into a OpenAPI specification.

Unfortunately, [the official Swagger Core project](https://github.com/swagger-core/) does not provide a reader implementation compatible with Spark APIs. It only offers a [JAX-RS-specific implementation](https://github.com/swagger-api/swagger-core/blob/master/modules/swagger-jaxrs2/src/main/java/io/swagger/v3/jaxrs2/Reader.java). While the [spark-swagger](https://github.com/manusant/spark-swagger) library is available as an alternative, its approach to describing APIs is programmatic and incompatible with the annotation-based method proposed in this RFC.

As a result, a custom reader will need to be implemented within the Uyuni codebase to generate the OpenAPI specification. This custom reader will closely resemble the JAX-RS reader, with minor modifications to accommodate Spark APIs. Specifically, it will need to adapt how routes are detected, as the JAX-RS reader relies on annotations such as `javax.ws.rs.Path` and HTTP method annotations (`@GET`, `@PUT`, `@POST`, `@DELETE`, etc).

It is worth noting that although this custom reader will introduce new code to maintain, it will replace the existing Doclet code currently used to generate API documentation. This transition will streamline the process and align it with modern standards.


#### C. Swagger UI

The generated OpenAPI specification will be seamlessly integrated into the Uyuni web UI using Swagger UI, enabling users to interact with API endpoints directly through the interface without requiring any coding.

To implement this feature, the [swagger-ui-react](https://www.npmjs.com/package/swagger-ui-react) library will be utilized. This library simplifies integration by allowing the specification to be passed directly to the SwaggerUI component, for example: `<SwaggerUI spec={uyuniSpec} />`.

Given the large number of endpoints provided by the Uyuni API, the UI will display endpoints categorized by namespaces. Users will have the ability to switch between namespaces and view the corresponding endpoints through a selection interface within the web UI. This approach ensures that the interface remains navigable and user-friendly, even with a substantial volume of endpoints.

Additionally, the web UI can incorporate supplementary documentation, including general descriptions, detailed instructions, and code examples, further enhancing the usability and functionality of the platform.


### Drawbacks
- Custom API reader maintenance.
  - Implementing a custom OpenAPI reader for Spark APIs introduces additional maintenance overhead. Unlike the JAX-RS reader provided by Swagger Core, the custom reader will require ongoing updates to accommodate changes in the Uyuni codebase or the Swagger/OpenAPI libraries.
- Initial Development Complexity
  - Creating the one-time scanner tool to automate the migration of existing Javadoc-based documentation adds complexity. While this tool will simplify the process, its development and validation represent a time-intensive task.


### Alternatives

- Keep the documentation as it is, since it is stable and functional.
  - The existing documentation, while static and less interactive, is stable and functional. Retaining it avoids the need for migration and eliminates the development and maintenance effort associated with Swagger integration. However, this approach would not address the limitations of static documentation, such as lack of interactivity and adherence to industry standards.

- Keep the format for describing the documentation using JavaDocs and write a new Java Doclet to generate the OpenAPI specification by parsing the definitions in JavaDocs.
  - This alternative leverages existing documentation practices, reducing the migration effort while still enabling OpenAPI integration. However, it lacks the strong typing and standardized annotations provided by Swagger and could still result in non-standardized maintenance challenges.

- Adopt Programmatic API Description.
  - Use a library like spark-swagger to describe the APIs programmatically. This approach simplifies the need for custom tools but sacrifices the benefits of annotation-driven documentation, such as direct integration with Java syntax and better alignment with industry practices. Additionally, it would require significant rewriting of API descriptions in a new format.

- Incremental migration.
  - Rather than completely replacing the current API documentation, an alternative approach is to enhance the existing Java Doclet to support both Swagger annotations and Javadocs. This would make it possible to maintain the current API documentation while gradually building the new OpenAPI specification. The main advantage of this approach is a smoother transition process. However, a key disadvantage is the necessity of maintaining two different documentation approaches simultaneously.

