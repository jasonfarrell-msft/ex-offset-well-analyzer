using System.Text.Json;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Offset;

namespace DrillAdvisor.Web.Endpoints;

/// <summary>
/// Implements anonymous offset-well analysis operations.
/// </summary>
public static class OffsetAnalysisEndpoint
{
    /// <summary>
    /// Handles one offset analysis request.
    /// </summary>
    public static async Task<IResult> HandleAsync(
        HttpRequest request,
        IClientSourceIdentifier sourceIdentifier,
        IAnonymousOffsetAnalysisGate offsetAnalysisGate,
        IOffsetAnalysisService offsetAnalysisService,
        CancellationToken cancellationToken)
    {
        if (request.ContentLength > OffsetContract.MaximumRequestBodyBytes)
        {
            return Results.Problem(
                detail: "The request body is too large.",
                type: "https://drill-advisor.example/problems/request_body_too_large",
                statusCode: StatusCodes.Status413PayloadTooLarge,
                title: "Request too large",
                extensions: new Dictionary<string, object?>
                {
                    ["code"] = "request_body_too_large",
                });
        }

        byte[] requestBody;
        try
        {
            requestBody = await ReadRequestBodyAsync(
                    request.Body,
                    cancellationToken)
                .ConfigureAwait(false);
            if (requestBody.Length > OffsetContract.MaximumRequestBodyBytes)
            {
                return Results.Problem(
                    detail: "The request body is too large.",
                    type: "https://drill-advisor.example/problems/request_body_too_large",
                    statusCode: StatusCodes.Status413PayloadTooLarge,
                    title: "Request too large",
                    extensions: new Dictionary<string, object?>
                    {
                        ["code"] = "request_body_too_large",
                    });
            }
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return Results.Problem(
                detail: "The request body is too large.",
                type: "https://drill-advisor.example/problems/request_body_too_large",
                statusCode: StatusCodes.Status413PayloadTooLarge,
                title: "Request too large",
                extensions: new Dictionary<string, object?>
                {
                    ["code"] = "request_body_too_large",
                });
        }

        OffsetOperationRequest? parsedRequest;
        try
        {
            using var document = StrictJson.Parse(requestBody);
            if (!OffsetRequestParser.TryParseOperationRequest(
                    document.RootElement,
                    allowChatOperation: false,
                    out parsedRequest,
                    out _,
                    out _))
            {
                return InvalidRequestFailure();
            }
        }
        catch (JsonException)
        {
            return InvalidRequestFailure();
        }

        var admission = offsetAnalysisGate.TryAcquire(sourceIdentifier.GetSourceKey(request));
        if (!admission.IsAllowed)
        {
            request.HttpContext.Response.Headers.RetryAfter =
                admission.RetryAfterSeconds.ToString(
                    System.Globalization.CultureInfo.InvariantCulture);
            return Results.Problem(
                detail: admission.StatusCode == StatusCodes.Status429TooManyRequests
                    ? "The anonymous POC request limit was reached. Retry later."
                    : "The anonymous POC is temporarily unavailable.",
                type: $"https://drill-advisor.example/problems/{admission.Code}",
                statusCode: admission.StatusCode,
                title: admission.StatusCode == StatusCodes.Status429TooManyRequests
                    ? "Request limit reached"
                    : "Public offset analysis unavailable",
                extensions: new Dictionary<string, object?>
                {
                    ["code"] = admission.Code,
                });
        }

        using var admissionLease = admission.Lease;
        var response = await offsetAnalysisService
            .ExecuteAsync(parsedRequest!, cancellationToken)
            .ConfigureAwait(false);
        return Results.Json(
            response.Body,
            statusCode: response.StatusCode);
    }

    private static IResult InvalidRequestFailure()
    {
        var body = new FailureEnvelope
        {
            ContractVersion = OffsetContract.ContractVersion,
            QueryContractVersion = OffsetContract.ContractVersion,
            TransformationContractVersion = OffsetContract.TransformationContractVersion,
            DatasetVersion = OffsetContract.DatasetVersion,
            ReleaseId = OffsetContract.ReleaseId,
            ManifestSha256 = OffsetContract.ManifestSha256,
            Operation = null,
            Status = "error",
            Context = null,
            ContextHash = null,
            Evidence = null,
            Error = new ErrorEnvelope("INVALID_REQUEST", false),
        };
        return Results.Json(body, statusCode: StatusCodes.Status400BadRequest);
    }

    private static async Task<byte[]> ReadRequestBodyAsync(
        Stream requestBody,
        CancellationToken cancellationToken)
    {
        using var stream = new MemoryStream();
        var buffer = new byte[2048];
        while (true)
        {
            var read = await requestBody.ReadAsync(buffer, cancellationToken).ConfigureAwait(false);
            if (read == 0)
            {
                return stream.ToArray();
            }

            await stream.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
            if (stream.Length > OffsetContract.MaximumRequestBodyBytes)
            {
                throw new OperationCanceledException();
            }
        }
    }
}
