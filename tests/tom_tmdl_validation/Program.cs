using Microsoft.AnalysisServices.Tabular;

if (args.Length != 1)
{
    throw new ArgumentException("Pass the semantic model definition folder.");
}

var expectedChildren = new HashSet<string>
{
    "Wells",
    "Data Quality",
    "Categories",
};

static void Validate(Database database, HashSet<string> expectedChildren)
{
    foreach (var table in database.Model.Tables)
    {
        var duplicateNames = table.Columns
            .Select(column => column.Name)
            .Concat(table.Measures.Select(measure => measure.Name))
            .GroupBy(name => name, StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1)
            .Select(group => group.Key)
            .OrderBy(name => name)
            .ToList();

        if (duplicateNames.Count != 0)
        {
            throw new InvalidOperationException(
                $"{table.Name} has duplicate column/measure names: "
                + string.Join(", ", duplicateNames)
            );
        }

        Console.WriteLine(
            $"{table.Name}: {table.Columns.Count} columns and "
            + $"{table.Measures.Count} measures have unique object names."
        );
    }

    var relationships = database.Model.Relationships
        .OfType<SingleColumnRelationship>()
        .ToList();

    if (relationships.Count != expectedChildren.Count)
    {
        throw new InvalidOperationException(
            $"Expected {expectedChildren.Count} relationships; found {relationships.Count}."
        );
    }

    foreach (var relationship in relationships)
    {
        var child = relationship.FromColumn.Table.Name;
        var parent = relationship.ToColumn.Table.Name;
        if (!expectedChildren.Remove(child)
            || parent != "Dataset Metadata"
            || relationship.FromColumn.Name != "Dataset Version"
            || relationship.ToColumn.Name != "Dataset Version"
            || relationship.FromCardinality != RelationshipEndCardinality.Many
            || relationship.ToCardinality != RelationshipEndCardinality.One
            || relationship.CrossFilteringBehavior != CrossFilteringBehavior.OneDirection)
        {
            throw new InvalidOperationException(
                $"{relationship.Name}: From={child}.{relationship.FromColumn.Name} "
                + $"({relationship.FromCardinality}); "
                + $"To={parent}.{relationship.ToColumn.Name} "
                + $"({relationship.ToCardinality}); "
                + $"Filter={relationship.CrossFilteringBehavior}"
            );
        }

        Console.WriteLine(
            $"{relationship.Name}: From={child}.Dataset Version (Many); "
            + "To=Dataset Metadata.Dataset Version (One); Filter=OneDirection"
        );
    }

    if (expectedChildren.Count != 0)
    {
        throw new InvalidOperationException(
            $"Missing child relationships: {string.Join(", ", expectedChildren)}"
        );
    }
}

var database = TmdlSerializer.DeserializeDatabaseFromFolder(args[0]);
Validate(database, new HashSet<string>(expectedChildren));

var roundTripFolder = Path.Combine(
    Path.GetTempPath(),
    $"drillrun-tmdl-roundtrip-{Guid.NewGuid():N}"
);
try
{
    TmdlSerializer.SerializeDatabaseToFolder(database, roundTripFolder);
    var roundTrippedDatabase =
        TmdlSerializer.DeserializeDatabaseFromFolder(roundTripFolder);
    Validate(roundTrippedDatabase, new HashSet<string>(expectedChildren));
}
finally
{
    if (Directory.Exists(roundTripFolder))
    {
        Directory.Delete(roundTripFolder, recursive: true);
    }
}
