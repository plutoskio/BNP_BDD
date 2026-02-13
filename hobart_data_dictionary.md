# Hobart Data Dictionary

**Total Tables:** 13

**Total Fields:** 171

---

## Table of Contents

1. [Activity](#activity) (34 fields)
2. [BUSINESSLINE](#businessline) (2 fields)
3. [BUSINESSLINE_ACTIVITY](#businessline-activity) (2 fields)
4. [BUSINESSLINE_PROCESS](#businessline-process) (2 fields)
5. [CATEGORY](#category) (2 fields)
6. [DESK_BUSINESSLINE_LINK](#desk-businessline-link) (4 fields)
7. [HISTORY_SR](#history-sr) (6 fields)
8. [History_Activity](#history-activity) (6 fields)
9. [History_Communication](#history-communication) (6 fields)
10. [JUR_USER](#jur-user) (3 fields)
11. [LABEL](#label) (2 fields)
12. [SR](#sr) (54 fields)
13. [SRCONTACT](#srcontact) (48 fields)

---


## Activity

**Field Count:** 34

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ACCEPTED_DATE` | TIMESTAMP(6) | - | Date and Time of Activity accepted by Activity Owner • Activity is Related to Task feature in Hobart - refering to the  date and time when the Task is accepted by Task Owner |
| `ACTNUMBER` | VARCHAR2 (50 CHAR) | 50 CHAR | Activity number • Related to Task feature in Hobart - refering to the Task Reference Number |
| `CHASER_NUMBER` | NUMBER(5,0) | - | Status of Activity • Related to Task feature in Hobart - Status of the Task |
| `CHECKERDATE` | TIMESTAMP(6) | - | Date and Time on which Checker completed the Checking of Activity • Related to Task feature in Hobart - refering to the date and time when Checker of the Task completed checking activity |
| `CHECKERUSER_ID` | NUMBER(15,0) | - | Technical ID of the user who has been assigned as Checker of the activity • Related to Task feature in Hobart - refering to the technica ID of the user that is assigned as checker of the Task |
| `CLOSINGDATE` | TIMESTAMP(6) | - | Closing date and time of the Activity • Related to Task feature in Hobart - refering to the  date and time when Task is closed |
| `COMPLETIONDATE` | TIMESTAMP(6) | - | Closing date and time of the Activity • Related to Task feature in Hobart - refering to the  date and time when Task is completed |
| `CRAFT_ACTIVITY_ID` | NUMBER(15,0) | - | Not being used in application • N/A |
| `CREATIONDATE` | TIMESTAMP(6) | - | Creation date and Time of Activity • Related to Task feature in Hobart - refering to the  date and time when Task is created |
| `CREATOR_DESK_ID` | NUMBER(15,0) | - | Technical ID of the Desk which creator belongs to • Related to Task feature in Hobart - refering to the Desk to which the Task creator belongs |
| `CREATOR_USER_ID` | NUMBER(15,0) | - | Technical ID of User who created the activity • Related to Task feature in Hobart - refering to the ID of the Task creator |
| `EXPIRATION_DATE` | TIMESTAMP(6) | - | Used in task audit to check the expiration date of the task • Related to Task feature in Hobart - refering to the  expiration date of the Task |
| `ID` | NUMBER(15,0) | - | Technical ID of the table to identify SR Activity |
| `IMPORTANCE_ID` | NUMBER(15,0) | - | Represent Activity Importance - eg: Normal • Related to Task feature in Hobart - refering to the importance of the Task |
| `IS_ACCEPTED` | NUMBER(1,0) | - | To represent if user has accepted the Task • Related to Task feature in Hobart - to identify if a user accepted the Task |
| `IS_DRAFT` | NUMBER(1,0) | - | To identify if the activity current status is draft • Related to Task feature in Hobart - when Task is in draft status |
| `IS_QUICK_TASK` | NUMBER(1,0) | - | Identify if Activity conducted as Quick Task • Related to Task feature in Hobart - Task can be accepted as quick task or Task Request. |
| `JUR_ASSIGNEDGROUP_ID` | NUMBER(15,0) | - | Technical ID of the desk of the user who created activity • Related to Task feature in Hobart - ID if the Desk of the user that created the Task |
| `JUR_ASSIGNEDUSER_ID` | NUMBER(15,0) | - | Technical ID of the user who currently have assigned activity • Related to Task feature in Hobart - ID of user that assigned the Task |
| `JUR_OWNER_ID` | NUMBER(15,0) | - | Not being used in application • N/A |
| `JUR_OWNERGROUP_ID` | NUMBER(15,0) | - | Not being used in application • N/A |
| `LAST_UPDATE_BY_DESK` | NUMBER(15,0) | - | Technical ID of the Desk which belongs to the user who updated the task • Related to Task feature in Hobart - ID of the Desk which belongs to the user who updated the task |
| `NOTIFICATIONDATE` | TIMESTAMP(6) | - | Data and Time when the task is notified to the user • Related to Task feature in Hobart - Data and Time when the task is notified to the user |
| `NOTIFIED` | NUMBER(1,0) | - | Not being used in application • N/A |
| `PRODUCERDATE` | TIMESTAMP(6) | - | Date and Time at which Activity producer completed production • Related to Task feature in Hobart - date & time when the Task Producer completes production (Task workflow production & check) |
| `PRODUCERUSER_ID` | NUMBER(15,0) | - | Technical ID of the user who has worked/produced the activity • Related to Task feature in Hobart - ID of the user who produced the Task |
| `REJECTED_DATE` | TIMESTAMP(6) | - | Date and Time of Activity rejected by Activity Owner • Related to Task feature in Hobart - date & time when task is rejectedby the task owner |
| `RESOLUTION_LABEL_ID` | NUMBER(15,0) | - | Not being used in application • N/A |
| `SR_ID` | NUMBER(15,0) | - | Technical ID of SR on which activity is performed • Related to Task feature in Hobart - ID of the Service Request in which the Task was created |
| `STATUS_ID` | NUMBER(15,0) | - | Activity status ID to denote Activity status • Related to Task feature in Hobart - ID to identify Task Status |
| `TASK_NUMBER` | NUMBER | - | Denote the sequence of Task associated in the SR • Related to Task feature in Hobart - Task Reference sequence number |
| `TYPE_ID` | NUMBER(15,0) | - | Activity Type ID to represent Activity Type • Related to Task feature in Hobart - to identify the Task Type, that can be Action, Information or Technical |
| `UPDATE_DATE` | TIMESTAMP(6) | - | Date and Time of Update made on the activity • Related to Task feature in Hobart - date & time of task update |
| `WORKFLOW_ID` | NUMBER(15,0) | - | To represent Task Workflow type • Related to Task feature in Hobart - to identify task workflow, that can be "simple" or "production & check" |



## BUSINESSLINE

**Field Count:** 2

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ID` | NUMBER | - |  • ID of the Business Line |
| `NAME` | VARCHAR2 (50 CHAR) | 50 CHAR | Defines the parameter of the Business • Name of the Busness Line = BP2S |



## BUSINESSLINE_ACTIVITY

**Field Count:** 2

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ID` | NUMBER | - |  • ID of the Business Line Activity |
| `NAME` | VARCHAR2 (100 CHAR) | 100 CHAR | Defines the activity to which the SR desk belongs to • Name of the Business Line Activity, that can be for instance BSO, IFSO, Transversal... |



## BUSINESSLINE_PROCESS

**Field Count:** 2

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ID` | NUMBER | - |  • ID of Business Line Process |
| `NAME` | VARCHAR2 (100 CHAR) | 100 CHAR | Defines the process which the SR desk carries out, and is linked to the Desk Business Activity • Name of Business Line Process, that can be for instance Cash, Local Settlement, Income/Tax, Fund Admin, Data Admin... |



## CATEGORY

**Field Count:** 2

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ID` | NUMBER(15,0) | - |  • ID of SR Category |
| `NAME` | VARCHAR2 (40 CHAR) | 40 CHAR | This field helps to categorize the SR which is a custom set of values set up on each desk based on the desk activity • Name of SR Category |



## DESK_BUSINESSLINE_LINK

**Field Count:** 4

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `BUSINESSLINE_ACTIVITY_ID` | NUMBER | - |  • ID of the Business Line Activity of the Desk |
| `BUSINESSLINE_ID` | NUMBER | - |  • ID of the Business Line of the Desk |
| `BUSINESSLINE_PROCESS_ID` | NUMBER | - |  • ID of the Business Line Process of the Desk |
| `DESK_ID` | NUMBER | - |  • ID of the Desk |



## HISTORY_SR

**Field Count:** 6

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `
ACTION` | 
VARCHAR2 (64 CHAR) | 64 CHAR | Activity/Process steps (Action performed on the SR) • Actions performed in the SR can be: Create, edit, create & close, close, reassign, reopen, abandon, suspend... |
| `
ACTION_DATE` | 
TIMESTAMP(6) | - | Date and Time when the Activity was performed |
| `FIELD` | VARCHAR2 (255 CHAR) | 255 CHAR | Represent field name where update has made • Field Name in the SR can be: Summary, Description, Owner, Final Response Date... |
| `ID` | NUMBER(15,0) | - | Technical ID of the record |
| `SR_ID` | NUMBER(15,0) | - | Incremental Technical ID for SR Created |
| `USER_NAME` | VARCHAR2 (255 CHAR) | 255 CHAR | User name of the Hobart User |



## History_Activity

**Field Count:** 6

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ACTION` | VARCHAR2 (64 CHAR) | 64 CHAR | Indicate action performed by user • Refers to the action that is performed by a user in a Task |
| `ACTION_DATE` | TIMESTAMP(6) | - | Date and Time of Action Performed • Refers to the date & time of the action perfomed in a Task |
| `ACTIVITY_ID` | NUMBER(15,0) | - | Tehcnical ID of the activity in activity table • ID of the Task |
| `FIELD` | VARCHAR2 (255 CHAR) | 255 CHAR | Represent field name where update has made • The Field can be the owner, the status, a date... |
| `ID` | NUMBER(15,0) | - | Technical ID of the record |
| `USER_NAME` | VARCHAR2 (255 CHAR) | 255 CHAR | User name of the Hobart User |



## History_Communication

**Field Count:** 6

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ACTION` | VARCHAR2 (64 CHAR) | 64 CHAR | Indicate action performed by user • Communication always relates to emails - Possible actions in emails Inside a SR can be: save as draft, send, send for validation (4EC) |
| `ACTION_DATE` | TIMESTAMP(6) | - | Date and Time of Action Performed |
| `COMMUNICATION_ID` | NUMBER(15,0) | - | Tehcnical ID of the Email in Srcontact |
| `FIELD` | VARCHAR2 (255 CHAR) | 255 CHAR | Represent field name where update has made • The Field name can be the subject of the email, the priority of the email... |
| `ID` | NUMBER(15,0) | - | Technical ID of the record |
| `USER_NAME` | VARCHAR2 (255 CHAR) | 255 CHAR | User name of Hobart User |



## JUR_USER

**Field Count:** 3

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `
FIRST_NAME` | VARCHAR2 (40 CHAR) | 40 CHAR | First name of the Owner of SR |
| `ID` | NUMBER(15,0) | - |  • ID of the Hobart User |
| `LAST_NAME` | VARCHAR2 (40 CHAR) | 40 CHAR | Last Name of the Owner of SR |



## LABEL

**Field Count:** 2

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ID` | NUMBER(15,0) | - |  • ID of SR Status |
| `NAME` | VARCHAR2 (255 CHAR) | 255 CHAR | Current Status of the SR • Status of SR can be: Open, Ongoing, Closed, Reopened, Suspended, Abandoned, Completed... |



## SR

**Field Count:** 54

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `ACKNOWLEDGE_DATE` | TIMESTAMP(6) | - | Date and Time on which SR was Acknowledge by the user |
| `ALERT` | NUMBER(1,0) | - | This is to indicate if the SR is expired • If SR Due Date is passed, Hobart raises and Alert |
| `AUTO_SUGGEST` | VARCHAR2 (30 BYTE) | 30 BYTE | Output of Smart Classifier to provide options to the users • Some Desks have the Smart Classifier Feature, that creates SR Drafts (that can be accepted or rejected by the users) |
| `CALCDUEDATE` | VARCHAR2 (20 BYTE) | 20 BYTE | Not being used in application • N/A |
| `CATEGORY_ID` | NUMBER(15,0) | - |  • ID of the SR Category |
| `CHECKERDATE` | TIMESTAMP(6) | - | Date and Time of Checker completion • SRs can have a specific Workflow, that is "Production & Check". For those, this field refers to the date & time when checker completes his action |
| `CHECKERUSER_ID` | NUMBER(15,0) | - | Technical ID of the User • ID of the checker user |
| `CLOSINGDATE` | TIMESTAMP(6) | - | Defines the date the SR is closed |
| `CONFIRMATION_TO_BE_SENT` | NUMBER(1,0) | - | To Autosend/draft SR Acknowlegdment email • Hobart allows to have a specific configuration to create automatic acknowledgement emails in draft status |
| `CREATIONDATE` | TIMESTAMP(6) | - | Defines the date and time the SR is created |
| `CREATOR_ID` | NUMBER(15,0) | - | Technical ID of the User who created the SR |
| `DEMAND_DATE` | TIMESTAMP(6) | - | Date and Time on which SR was Requested • For example, when a SR is created from an email, the demand date is the date & time when the email was received |
| `EFFECTIVE_FIRST_RESPONSE_DATE` | TIMESTAMP(6) | - | Date and Time of SR Effective First Response based on User Action • When inside a SR, an email is sent, marked as "First Response" |
| `ESTIMATEDTIME` | NUMBER(20,0) | - | Not being used in application • N/A |
| `EXPECTED_ACKNOWLEDGEMENT_DATE` | TIMESTAMP(6) | - | Defines the date by when an acknowledgement has to be sent to the client from the SR • For the Desks that have a SLA defined to the Acknowldegment Deadline |
| `EXPECTED_FIRST_RESPONSE_DATE` | TIMESTAMP(6) | - | Defines the date by when the 1st response should be sent to the client from the SR • For the Desks that have a SLA defined to the First Response Deadline |
| `EXPIRATION_DATE` | TIMESTAMP(6) | - | Defines the date by when the SR is expected to be closed • All the Desks have a set up for the SLA Due Date, meaning that acording to that parametrization, each SR has an expected expiration date according to the Due Date Deadline |
| `FINAL_RESPONSE_DATE` | TIMESTAMP(6) | - | Date and Time of SR Final Response sent by the User • the Final Response Date & Date is the last sent email, or the closing date |
| `FIRST_ACTION_EMAIL_DATE` | TIMESTAMP(6) | - | Date and Time of Email being responded to the requestor |
| `HAS_NEW` | NUMBER(1,0) | - | Indicate if the SR has new email linked |
| `ID` | NUMBER(15,0) | - | Incremental Technical ID for SR Created |
| `INITIAL_TASK_ID` | NUMBER(15,0) | - | Refers to Parent Task ID of the Task Request • When a Task is accepted as Task Request, has the information about the parent Task ID |
| `INTERNAL_FLAG` | NUMBER(1,0) | - | To know whether the email is sent from internal / external. Used in inbox for email where we have INT/EXT column. Values that are stored in database are 1 or 0. • Hobart users can select most of the columns visible in the Inbox screen. Column INT/ EXT being visible will show wether the email is sent from internal or external domain |
| `IS_MULTICHANNEL_SR` | NUMBER(1,0) | - | Used in centric alert notification to check whether the SR is from multiple channels • N/A |
| `ISSCHEDULER` | NUMBER(1,0) | - | To indicate if that row is scheduler • Schedulers are scheduled SRs. An SR that is created with a certain frequency |
| `ISSUER` | VARCHAR2 (20 BYTE) | 20 BYTE | Represent SR Issuer Type • Possible Issuer Types are: Client, Third Party or Internal |
| `ISSUER_TYPE_VALUE` | NUMBER(2,0) | - | Defines if the value is filled in Issuer Type field or not • The Issuer Type Value > Client Name, Third Party Name, BNPP Contact Team are not mandatory to be filled. Hence, in some cases they are left blank |
| `JUR_ASSIGNEDGROUP_ID` | NUMBER(15,0) | - | Technical ID of the Hobart Desk for the user |
| `JUR_ASSIGNEE_ID` | NUMBER(15,0) | - |  |
| `JUR_DESK_ID` | NUMBER(15,0) | - |  • Desk ID |
| `LEAD_TIME_EX1` | VARCHAR2 (255 BYTE) | 255 BYTE | It is the difference between SR creation date and 1st email reception date (only business hours and working days are taken into account) |
| `LEAD_TIME_EX2` | VARCHAR2 (255 BYTE) | 255 BYTE | It is the difference between SR acknowledgement date and email reception date (only business hours and working days are taken into account) |
| `LEAD_TIME_EX3` | VARCHAR2 (255 BYTE) | 255 BYTE | It is the difference between final response date and 1st email reception date (only business hours and working days are taken into account) |
| `LEAD_TIME_EX4` | VARCHAR2 (255 BYTE) | 255 BYTE | It is the difference between SR acknowledgement date and SR creation date (only business hours and working days are taken into account) |
| `LEAD_TIME_EX5` | VARCHAR2 (255 BYTE) | 255 BYTE | It is the difference between Final response date and SR creation date (only business hours and working days are taken into account) |
| `NEXTACTNUMBER` | NUMBER(20,0) | - | The NEXTACTNUMBER field ensures that each task associated with a service request gets a unique and sequential task number. It starts from 1 and increments with each new task creation. |
| `PRIORITY_ID` | NUMBER(15,0) | - | Denotes the Priority of the SR • Pririty of SR can be: Critical, High, Normal, Low |
| `PRODUCERDATE` | TIMESTAMP(6) | - | Date and Time of Production completion • For SRs that have the workflow Production & Check |
| `PRODUCERUSER_ID` | NUMBER(15,0) | - | Technical ID of user who produced SR for Prod and Check workflow SR |
| `QUICK_ANSWER` | NUMBER(1,0) | - | Not being used in application • N/A |
| `QUICK_FULFILLMENT_ID` | NUMBER(15,0) | - | Represent SR Quick fill • Quick fills are  a quicker way to create Service Requests with pre-defined criteria such as: Type/Categories/Sub-categories/Priority/Channel. When creating the SR, you will still be able to update one of the fields. |
| `REMINDER_DATE` | TIMESTAMP(6) | - | Reminder Date and Time on SR based on Desk Configuration • Set up that is defined at Desk Level and will be populated in the SR |
| `REOPEN_DATE` | TIMESTAMP(6) | - | Date and Time on which SR was Reopened |
| `REPLY_TIME` | NUMBER(20,0) | - | Number of seconds taken by the desk user to respond to the requestor on email |
| `ROOTSR_ID` | NUMBER(15,0) | - | Refers to the Parent Scheduler of the scheduled SR |
| `SR_DRAFT_TYPE` | VARCHAR2 (10 BYTE) | 10 BYTE | Requestor mode of the Draft SR • Can be email, emessage |
| `SRNUMBER` | VARCHAR2 (255 CHAR) | 255 CHAR | Service Request (SR) identifier • Each SR has a Ref with the Desk Short Name + Trigram of the User that created the SR + Sequence number |
| `STATUS_ID` | NUMBER(15,0) | - |  • Status ID of the SR |
| `SUBCATEGORY_ID` | NUMBER(15,0) | - |  • Sub Category ID of the SR. Each SR has a Category and a Sub Category |
| `SUSPEND_DURATION` | VARCHAR2 (255 BYTE) | 255 BYTE | Time duration in which SR stays in Suspended in SR Status |
| `TREATMENT_TIME` | VARCHAR2 (255 BYTE) | 255 BYTE | Time taken to close the SR in hh:mm:ss • Time elapsed from Demand Date to Final Response Date |
| `TYPE_ID` | NUMBER(15,0) | - | Denotes SR Type • ID of the SR Type: Inquiry, To Do, Incident... |
| `UPDATE_DATE` | TIMESTAMP(6) | - | Date and Time on which Last Update made by the user |
| `WORKFLOW_ID` | NUMBER(15,0) | - | Represent SR Workflow detail • Workflow of SR can be Simple or Production & Check |



## SRCONTACT

**Field Count:** 48

| Field Name | Type | Length | Description |
|------------|------|--------|-------------|
| `
SR_ID` | NUMBER(15,0) | - |  |
| `AUTO_SUGGEST` | VARCHAR2 (30 BYTE) | 30 BYTE | Output of Smart Classifier to provide options to the users • Some Desks have the Smart Classifier Feature, that creates SR Drafts (that can be accepted or rejected by the users) |
| `CONFIRMATION_TO_BE_SENT` | NUMBER(1,0) | - | It is used to check whether the a confirmation is needed while sending an email. |
| `CREATIONDATE` | TIMESTAMP(6) | - | Date and Time of Email logged in the Hobart DB |
| `DATE_TIME_SENT` | TIMESTAMP(6) | - | Date and Time of Email Sent |
| `EMAIL_APPROVED_BY_ID` | VARCHAR2 (30 BYTE) | 30 BYTE | UID of user who approved email in 4 eye check • Hobart has 4EC feature, at Desk Level. When it is activated, the email is sent for approval, to be checked by another user of the Desk, before being send to the final recipients |
| `EMAIL_APPROVED_DATE` | TIMESTAMP(6) | - | Date and Time of Email approved in 4 eye check |
| `EMAIL_CATEGORY` | VARCHAR2 (20 BYTE) | 20 BYTE | To signify category of Email • Email Category can be for example > Normal |
| `EMAIL_REJECTED_BY_ID` | VARCHAR2 (30 BYTE) | 30 BYTE | UID of user who rejected email in 4 eye check |
| `EMAIL_REJECTED_DATE` | TIMESTAMP(6) | - | Date and Time of Email rejected in 4 eye check process |
| `EMAIL_SEND_FOR_APPROVAL_DATE` | TIMESTAMP(6) | - | Date and Time of Email send for 4 eye check |
| `EMAIL_SEND_FOR_APPROVAL_ID` | VARCHAR2 (30 BYTE) | 30 BYTE | UID of user who sent email for 4 eye check |
| `EMAIL_TYPE` | VARCHAR2 (255 BYTE) | 255 BYTE | Type of Email Body • Email body can be: text, table, picture... |
| `FIRST_READ_BY` | VARCHAR2 (80 CHAR) | 80 CHAR | User name who has read the email • User that first read an email |
| `FIRST_READ_DATE` | TIMESTAMP(6) | - | Date and Time the email as read |
| `FLAG_LABEL_ID` | NUMBER(38,0) | - | If the mail is flagged the respective ID is marked • Hobart allows to have flags at mailbox level. When the flags are set up, users have the change to flag the incoming emails in the Desk, and there is a specific Label/ ID |
| `FORWARDED_BY` | NUMBER(15,0) | - | UID of user who forwarded email |
| `FORWARDING_DATE` | TIMESTAMP(6) | - | Date and Time of Email when it is forwarded |
| `FOUR_EYE_CHECK_ENABLED` | NUMBER(1,0) | - | Represent Outbound email eligible for Four Eye Check • When outgoing emails have 4EC toggle active |
| `HAS_ATTACHMENT` | NUMBER(1,0) | - | Shows if Email has an attachment |
| `ID` | NUMBER(15,0) | - | Query Identifier (Email) • ID number for emails |
| `IMPORTANCE` | VARCHAR2 (6 BYTE) | 6 BYTE | Represent Email Category • Email importance can be: Normal, High, Low |
| `INTEGRATION_DATE` | TIMESTAMP(6) | - | Date and Time of Email Integerated in Hobart |
| `IS_AUTOLINK` | NUMBER(1,0) | - | Denotes if Email is automatically linked to SR |
| `IS_DR_REQUESTED` | NUMBER(1,0) | - | Not being used in application • N/A |
| `IS_DRAFT` | NUMBER(1,0) | - | Determin if the Email (Outbound) is draft or not |
| `IS_FORWARDED` | NUMBER(1,0) | - | Identifier to know if the email is forwarded |
| `IS_LOCKED` | NUMBER(1,0) | - | To indicate if the SR is locked • In case email is locked, linked to SR |
| `IS_RE_REQUESTED` | NUMBER(1,0) | - | Not being used in application • N/A |
| `IS_READ` | NUMBER(1,0) | - | If the Email is read by the desk user |
| `IS_RR_REQUEST` | NUMBER(1,0) | - | To check if the email is read or not - isReadReceiptRequested |
| `JUR_CREATOR_ID` | NUMBER(15,0) | - | Technical ID of the user who created the Email |
| `JUR_LOCKED_BY` | NUMBER(15,0) | - | Technical ID for the user who locked the SR |
| `LAST_ARCHIVED_BY` | VARCHAR2 (80 CHAR) | 80 CHAR | User name who has archived the email • Hobart allows the archival of emails > user name of user performing this action |
| `LAST_ARCHIVED_DATE` | TIMESTAMP(6) | - | Date and Time of Email archived |
| `LAST_LINKED_BY` | VARCHAR2 (80 CHAR) | 80 CHAR | User name who has linked the email • Related to manual linkage of email to SR |
| `LAST_LINKED_DATE` | TIMESTAMP(6) | - | Date and Time of when the email is linked to SR |
| `LAST_REMOVED_BY` | VARCHAR2 (80 CHAR) | 80 CHAR | User name who has deleted the email from Hobart |
| `LAST_REMOVED_DATE` | TIMESTAMP(6) | - | Date and Time of Deletion of Email |
| `MAILBOX_ID` | NUMBER(15,0) | - | Desk ID on which Email is linked to |
| `MEDIUM_ID` | NUMBER(15,0) | - | Signify the Medium of Interaction i.e. Email • Medium can be: Email, Chat, Face to Face, Fax, Paper, Phone, Swift, System, Web Portal |
| `OUTBOUND` | NUMBER(1,0) | - | Related Sent email count (associated with a SR) is computed using sql queries & displayed in the UI (the count is not held in a column in the DB) • Number of outgoing emails linked to a SR |
| `OUTBOUND` | NUMBER(1,0) | - | Related Received count (associated with a SR) is computed using sql queries & displayed in the UI (the count is not held in a column in the DB) • Number of incoming emails linked to a SR |
| `RECEPTION_DATE` | TIMESTAMP(6) | - | Date and Time of Email received |
| `SENSITIVITY_ID` | NUMBER(15,0) | - | Not being used in application • N/A |
| `STATUS` | NUMBER(2,0) | - | To retrieve the status of the received email. We are storing nearly 27 status like NEW, READ, LINKED_TO_EXISTING_SR, DELETED, NEW_AUTO_LINKED … |
| `SUCCESS` | NUMBER(1,0) | - | Not being used in application • N/A |
| `TEMPLATE_APPLIED` | NUMBER(1,0) | - | Not being used in application • N/A |

