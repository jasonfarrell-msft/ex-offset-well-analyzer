using System.Text;
using System.Text.Json;
using System.Linq;

namespace DrillAdvisor.Api.Tests;

public sealed class NotebookPublicationModeTests
{
    [Fact]
    public void CurrentNotebook_DefaultsToPointerActivation()
    {
        var notebook = ReadTrackedNotebook();
        var parameterSource = ReadParametersCellSource(notebook);
        var source = ReadTrackedNotebookPublicationSource(notebook);

        Assert.Contains("ACTIVATE_RELEASE_POINTER = True", parameterSource, StringComparison.Ordinal);
        Assert.Contains("globals().get(\"ACTIVATE_RELEASE_POINTER\", DEFAULT_ACTIVATE_RELEASE_POINTER)", source, StringComparison.Ordinal);
        Assert.Contains("INVALID_ACTIVATE_RELEASE_POINTER_PARAMETER", source, StringComparison.Ordinal);
        Assert.Contains("if ACTIVATE_RELEASE_POINTER and not release_already_active:", source, StringComparison.Ordinal);
    }

    [Fact]
    public void CurrentNotebook_HasStageOnlyGuardrailsForOptionalMode()
    {
        var source = ReadTrackedNotebookPublicationSource(ReadTrackedNotebook());

        Assert.Contains("\"STAGED_ONLY_NO_POINTER_UPDATE\"", source, StringComparison.Ordinal);
        Assert.Contains("active_release_id if not ACTIVATE_RELEASE_POINTER else RELEASE_ID", source, StringComparison.Ordinal);
        Assert.Contains("STAGE_ONLY_POINTER_UNEXPECTED", source, StringComparison.Ordinal);
        Assert.Contains("active_pointer[0][\"active_release_id\"] == active_release_id", source, StringComparison.Ordinal);
    }

    [Fact]
    public void ReadyTransitionOccursAfterEvidenceValidation()
    {
        var source = ReadTrackedNotebookPublicationSource(ReadTrackedNotebook());

        var evidenceInsert = source.IndexOf(
            "INSERT INTO {PUBLICATION_EVIDENCE_TABLE}",
            StringComparison.Ordinal);
        var readyAfterEvidence = source.IndexOf(
            "RELEASE_NOT_READY_AFTER_EVIDENCE",
            StringComparison.Ordinal);
        var pointerActivation = source.LastIndexOf(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target",
            StringComparison.Ordinal);

        Assert.True(evidenceInsert >= 0, "evidence insert not found");
        Assert.True(readyAfterEvidence >= 0, "post-evidence ready gate not found");
        Assert.True(evidenceInsert < readyAfterEvidence, "ready transition must follow evidence persistence");
        Assert.True(pointerActivation > readyAfterEvidence, "pointer activation must happen after ready transition");
    }

    private static JsonDocument ReadTrackedNotebook()
    {
        var root = FindRepositoryRoot();
        var path = Path.Combine(
            root,
            "fabric",
            "nb_10_build_drillrun_summary.Notebook",
            "notebook-content.ipynb");
        return JsonDocument.Parse(File.ReadAllText(path, Encoding.UTF8));
    }

    private static string ReadParametersCellSource(JsonDocument notebook)
    {
        foreach (var cell in notebook.RootElement.GetProperty("cells").EnumerateArray())
        {
            if (cell.TryGetProperty("metadata", out var metadata)
                && metadata.TryGetProperty("tags", out var tags))
            {
                var hasParametersTag = tags.EnumerateArray()
                    .Any(tag => string.Equals(tag.GetString(), "parameters", StringComparison.Ordinal));
                if (hasParametersTag)
                {
                    return JoinCellSource(cell);
                }
            }
        }

        throw new InvalidOperationException("Notebook parameters cell not found.");
    }

    private static string ReadTrackedNotebookPublicationSource(JsonDocument notebook)
    {
        var cells = notebook.RootElement.GetProperty("cells");
        var lastCell = cells[cells.GetArrayLength() - 1];
        return JoinCellSource(lastCell);
    }

    private static string JoinCellSource(JsonElement cell)
    {
        var source = new StringBuilder();
        foreach (var line in cell.GetProperty("source").EnumerateArray())
        {
            source.Append(line.GetString());
        }

        return source.ToString();
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "fabric", "nb_10_build_drillrun_summary.Notebook", "notebook-content.ipynb")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found.");
    }
}
