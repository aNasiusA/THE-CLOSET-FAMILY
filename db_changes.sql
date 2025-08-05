ALTER TABLE Members 
ADD IsInvitee BIT DEFAULT 0;
GO
-- Update existing event registrants to be marked as invitees if they aren't members
UPDATE m
SET IsInvitee = 1
FROM Members m
WHERE NOT EXISTS (
    SELECT 1 FROM MemberMinistries mm WHERE mm.MemberID = m.MemberID
)
AND EXISTS (
    SELECT 1 FROM EventRegistrations er WHERE er.MemberID = m.MemberID
);
