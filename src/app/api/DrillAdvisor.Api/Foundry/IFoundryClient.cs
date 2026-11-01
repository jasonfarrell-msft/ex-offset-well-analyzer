using DrillAdvisor.Api.Models;

namespace DrillAdvisor.Api.Foundry;

/// <summary>
/// Calls the Microsoft Foundry project APIs with application identity.
/// </summary>
public interface IFoundryClient
{
    /// <summary>
    /// Sends a chat message to the configured Foundry agent.
    /// </summary>
    /// <param name="message">The unmodified user message.</param>
    /// <param name="conversationId">An existing conversation ID, or <see langword="null"/> to create one.</param>
    /// <param name="additionalInstructions">
    /// Optional request-scoped instructions that augment agent-level instructions.
    /// </param>
    /// <param name="cancellationToken">A token that cancels the upstream operation.</param>
    /// <returns>The safe, parsed Foundry reply.</returns>
    Task<FoundryReply> SendAsync(
        string message,
        string? conversationId,
        string? additionalInstructions,
        CancellationToken cancellationToken);
}
