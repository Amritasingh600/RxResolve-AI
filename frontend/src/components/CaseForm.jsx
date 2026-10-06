// The case input fields, shared by "Create case" and "Edit case".

export const EMPTY_CASE = {
  patient_id: "",
  claim_id: "",
  medication: "",
  insurance: "",
  rejection_code: "",
  rejection_message: "",
  quantity: "",
  date_of_service: "",
  prescriber: "",
  notes: "",
};

const REQUIRED = ["patient_id", "claim_id", "medication", "insurance", "rejection_message"];

export function validateCase(form) {
  const errors = {};
  REQUIRED.forEach((key) => {
    if (!String(form[key] || "").trim()) errors[key] = "Required";
  });
  return errors;
}

// Convert a case from the API into form values (null -> "").
export function caseToForm(caseData) {
  const form = {};
  Object.keys(EMPTY_CASE).forEach((key) => {
    form[key] = caseData[key] ?? "";
  });
  return form;
}

function Field({ name, label, form, setForm, errors, required, type = "text", maxLength, placeholder, textarea }) {
  const props = {
    id: name,
    value: form[name] ?? "",
    maxLength,
    placeholder,
    onChange: (e) => setForm({ ...form, [name]: e.target.value }),
    "aria-invalid": errors[name] ? "true" : undefined,
  };
  return (
    <label className={`field ${textarea ? "span-2" : ""}`} htmlFor={name}>
      <span>
        {label} {required && <span className="required">*</span>}
      </span>
      {textarea ? <textarea rows={3} {...props} /> : <input type={type} {...props} />}
      {errors[name] && <span className="field-error">{errors[name]}</span>}
    </label>
  );
}

export default function CaseForm({ form, setForm, errors = {} }) {
  const common = { form, setForm, errors };
  return (
    <div className="form-grid">
      <Field name="patient_id" label="Patient ID" required maxLength={50} placeholder="e.g. PT-10011" {...common} />
      <Field name="claim_id" label="Prescription / claim ID" required maxLength={50} placeholder="e.g. RX-50011" {...common} />
      <Field name="medication" label="Medication name" required maxLength={120} placeholder="e.g. ExampleMed 50 mg" {...common} />
      <Field name="insurance" label="Insurance / payer" required maxLength={120} placeholder="e.g. DemoHealth" {...common} />
      <Field name="rejection_code" label="Rejection code" maxLength={20} placeholder="e.g. PA001 or 75" {...common} />
      <Field name="quantity" label="Quantity" maxLength={50} placeholder="e.g. 30" {...common} />
      <Field name="date_of_service" label="Date of service" type="date" {...common} />
      <Field name="prescriber" label="Prescriber" maxLength={120} placeholder="Name / NPI (optional)" {...common} />
      <Field
        name="rejection_message"
        label="Rejection message"
        required
        textarea
        maxLength={2000}
        placeholder="Copy the exact message from the payer response"
        {...common}
      />
      <Field name="notes" label="Additional notes" textarea maxLength={4000} {...common} />
    </div>
  );
}
