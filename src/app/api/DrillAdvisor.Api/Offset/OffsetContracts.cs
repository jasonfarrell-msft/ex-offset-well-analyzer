using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Serialization;

namespace DrillAdvisor.Api.Offset;

public static class OffsetContract
{
    // Legacy v1 constants retained for compatibility with existing callers/tests.
    public const string ContractVersion = "offset-well-analysis-v1";
    public const string ManifestSha256 =
        "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d";
    public const string ReleaseId = $"v1.1.0:{ManifestSha256}";
    public const string DatasetVersion = "v1.1.0";
    public const string TransformationContractVersion = "1.1.0";
    public const string Disclosure =
        "SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY";
    public const string CoordinateFrameId = "SYN-LOCAL-FT-V1";
    public const string LocationSemantics = "SYNTHETIC_SURFACE_WELLHEAD";
    public const string CoordinateUnits = "ft";
    public const int MaximumRequestBodyBytes = 8_192;
    public const int MaximumMessageLength = 2_000;
}

public sealed record OffsetContractSpec(
    string ContractVersion,
    string ManifestSha256,
    string ReleaseId,
    string DatasetVersion,
    string TransformationContractVersion,
    string Disclosure);

public static class OffsetContractVersions
{
    public static readonly OffsetContractSpec V1 = new(
        ContractVersion: "offset-well-analysis-v1",
        ManifestSha256: "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
        ReleaseId: "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
        DatasetVersion: "v1.1.0",
        TransformationContractVersion: "1.1.0",
        Disclosure: "SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY");

    public static readonly OffsetContractSpec V2 = new(
        ContractVersion: "offset-well-analysis-v2",
        ManifestSha256: "6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
        ReleaseId: "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
        DatasetVersion: "v1.2.0",
        TransformationContractVersion: "1.2.0",
        Disclosure: "SYNTHETIC DATA • v1.2.0 • DEVELOPMENT / OFFSET COMPARISON ONLY");

    public static bool TryResolve(
        string contractVersion,
        string releaseId,
        out OffsetContractSpec contract)
    {
        contract = null!;
        if (string.Equals(contractVersion, V1.ContractVersion, StringComparison.Ordinal)
            && string.Equals(releaseId, V1.ReleaseId, StringComparison.Ordinal))
        {
            contract = V1;
            return true;
        }

        if (string.Equals(contractVersion, V2.ContractVersion, StringComparison.Ordinal)
            && string.Equals(releaseId, V2.ReleaseId, StringComparison.Ordinal))
        {
            contract = V2;
            return true;
        }

        return false;
    }
}

public static class OffsetFormats
{
    public static string CanonicalDecimal(decimal value) =>
        value.ToString("0.############", CultureInfo.InvariantCulture);

    public static string RatioSix(decimal numerator, decimal denominator)
    {
        var rounded = decimal.Round(
            numerator / denominator,
            6,
            MidpointRounding.AwayFromZero);
        return rounded.ToString("0.000000", CultureInfo.InvariantCulture);
    }

    public static string DistanceOne(decimal squaredFeet)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(squaredFeet);

        var value = Math.Sqrt(Convert.ToDouble(squaredFeet, CultureInfo.InvariantCulture));
        var rounded = Math.Round(value, 1, MidpointRounding.AwayFromZero);
        return rounded.ToString("0.0", CultureInfo.InvariantCulture);
    }
}

public sealed record OffsetCriteria(
    [property: JsonPropertyName("radiusFt")] string RadiusFt,
    [property: JsonPropertyName("formationMatch")] bool FormationMatch,
    [property: JsonPropertyName("holeSizeMatch")] bool HoleSizeMatch,
    [property: JsonPropertyName("mdOverlap")] bool MdOverlap);

public sealed record OffsetContext(
    [property: JsonPropertyName("targetId")] string TargetId,
    [property: JsonPropertyName("criteria")] OffsetCriteria Criteria,
    [property: JsonPropertyName("selectedWellIds")] IReadOnlyList<string> SelectedWellIds,
    [property: JsonPropertyName("contextRevision")] long ContextRevision);

public sealed record OffsetOperationRequest(
    string Operation,
    string ContractVersion,
    string ReleaseId,
    OffsetContractSpec Contract,
    OffsetContext? Context,
    string? Message,
    string? ConversationId);

public sealed record TargetRow(
    string TargetId,
    string RecordKind,
    string BasinName,
    string FieldName,
    string ExpectedFormationName,
    string PlannedTrajectoryProfile,
    string PlannedHoleSizeIn,
    string PlannedMdMinFt,
    string PlannedMdMaxFt,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string SurfaceXFt,
    string SurfaceYFt,
    string ReferenceDatasetVersion,
    string ReferenceManifestSha256,
    bool IsSynthetic,
    string? PlannedBitType,
    string? PlannedBhaType,
    string? PlannedMudType);

public sealed record OffsetSectionRow(
    string TargetId,
    string WellId,
    string WellName,
    string BasinName,
    string FieldName,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string SurfaceXFt,
    string SurfaceYFt,
    string? SectionId,
    string? FormationName,
    string? HoleSizeIn,
    string? StartMdFt,
    string? EndMdFt,
    string? TrajectoryProfile,
    int AcceptedRunCount,
    string? AcceptedFootageFt,
    string? AcceptedDurationHours,
    int QuarantinedRunCount,
    int WarningRunCount,
    int WarningSectionCount,
    int WarningIssueCount);

public sealed record OffsetRunConfigurationRow(
    string TargetId,
    string WellId,
    string? BitType,
    string? BhaType,
    string? MudType,
    string? MudWeightPpg,
    string? MudFunnelViscositySec,
    int AcceptedRunCount,
    string? AcceptedFootageFt,
    string? AcceptedDurationHours);

public sealed record OffsetRunEventRow(
    string TargetId,
    string WellId,
    string EventType,
    string EventSubtype,
    int EventCount,
    string EventDurationHours);

public static class OffsetContextHasher
{
    private static readonly System.Text.Json.JsonSerializerOptions HashJsonOptions =
        new()
        {
            PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase,
            WriteIndented = false,
        };

    public static string Hash(
        OffsetContext context,
        string releaseId,
        string contractVersion)
    {
        var normalized = new
        {
            contractVersion,
            releaseId,
            targetId = context.TargetId,
            criteria = new
            {
                radiusFt = OffsetFormats.CanonicalDecimal(ParseDecimal(context.Criteria.RadiusFt)),
                context.Criteria.FormationMatch,
                context.Criteria.HoleSizeMatch,
                context.Criteria.MdOverlap,
            },
            selectedWellIds = context.SelectedWellIds,
            context.ContextRevision,
        };
        var bytes = Encoding.UTF8.GetBytes(
            System.Text.Json.JsonSerializer.Serialize(
                normalized,
                HashJsonOptions));
        return Convert.ToHexString(SHA256.HashData(bytes))
            .ToLowerInvariant();
    }

    public static decimal ParseDecimal(string text)
    {
        if (!decimal.TryParse(
                text,
                NumberStyles.AllowLeadingSign | NumberStyles.AllowDecimalPoint,
                CultureInfo.InvariantCulture,
                out var value))
        {
            throw new FormatException("Invalid decimal text.");
        }

        return value;
    }
}
