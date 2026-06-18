use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use serde_json::Value;
use winterfell::crypto::hashers::Blake3_256;
use winterfell::crypto::{DefaultRandomCoin, MerkleTree};
use winterfell::math::{fields::f128::BaseElement, FieldElement, StarkField, ToElements};
use winterfell::matrix::ColMatrix;
use winterfell::{
    verify, AcceptableOptions, Air, AirContext, Assertion, AuxRandElements, BatchingMethod,
    CompositionPoly, CompositionPolyTrace, ConstraintCompositionCoefficients,
    DefaultConstraintCommitment, DefaultConstraintEvaluator, DefaultTraceLde, EvaluationFrame,
    FieldExtension, PartitionOptions, Proof, ProofOptions, Prover, StarkDomain, TraceInfo,
    TracePolyTable, TraceTable, TransitionConstraintDegree,
};

const TRACE_LENGTH: usize = 8;
const CLOCK_START: u128 = 0;
const FIELD_MODULUS: u128 = 340282366920938463463374557953744961537;
const NULLIFIER_DOMAIN: u128 = 101;
const COMMITMENT_DOMAIN: u128 = 202;

type HashFn = Blake3_256<BaseElement>;
type VC = MerkleTree<HashFn>;
type RandomCoin = DefaultRandomCoin<HashFn>;
type TraceLde<E> = DefaultTraceLde<E, HashFn, VC>;
type ConstraintEvaluator<'a, E> = DefaultConstraintEvaluator<'a, ReferendumAir, E>;
type ConstraintCommitment<E> = DefaultConstraintCommitment<E, HashFn, VC>;

#[derive(Debug, Clone, Copy)]
struct ReferendumWitness {
    vote_value: u128,
    registered_flag: u128,
    already_voted_flag: u128,
    event_id_scalar: u128,
    voter_secret: u128,
    ballot_salt: u128,
}

#[derive(Debug, Clone, Copy)]
struct PublicInputValues {
    event_id_scalar: u128,
    nullifier: u128,
    vote_commitment: u128,
}

#[derive(Debug, Clone, Copy)]
struct PublicInputs {
    event_id_scalar: BaseElement,
    nullifier: BaseElement,
    vote_commitment: BaseElement,
}

impl ToElements<BaseElement> for PublicInputs {
    fn to_elements(&self) -> Vec<BaseElement> {
        vec![self.event_id_scalar, self.nullifier, self.vote_commitment]
    }
}

struct ReferendumAir {
    context: AirContext<BaseElement>,
    public_inputs: PublicInputs,
    trace_length: usize,
}

impl Air for ReferendumAir {
    type BaseField = BaseElement;
    type PublicInputs = PublicInputs;

    fn new(trace_info: TraceInfo, public_inputs: PublicInputs, options: ProofOptions) -> Self {
        assert_eq!(8, trace_info.width());
        let degrees = vec![
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(3),
            TransitionConstraintDegree::new(3),
        ];
        let trace_length = trace_info.length();
        let num_assertions = 10;

        Self {
            context: AirContext::new(trace_info, degrees, num_assertions, options),
            public_inputs,
            trace_length,
        }
    }

    fn context(&self) -> &AirContext<Self::BaseField> {
        &self.context
    }

    fn evaluate_transition<E: FieldElement<BaseField = Self::BaseField> + From<Self::BaseField>>(
        &self,
        frame: &EvaluationFrame<E>,
        _periodic_values: &[E],
        result: &mut [E],
    ) {
        let current = frame.current();
        let next = frame.next();
        let one = E::ONE;

        result[0] = next[0] - current[0] - one;
        result[1] = next[1] - current[1];
        result[2] = next[2] - current[2];
        result[3] = next[3] - current[3];
        result[4] = next[4] - current[4];
        result[5] = next[5] - current[5];
        result[6] = next[6] - current[6];
        result[7] = next[7] - current[7];
        result[8] = current[1] * (current[1] - one);
        result[9] = current[2] - one;
        result[10] = current[3];
        result[11] = current[4] - (current[2] * (one - current[3]));
        result[12] = current[4] - one;
        result[13] =
            E::from(self.public_inputs.nullifier) - prototype_hash(current[6], current[5], NULLIFIER_DOMAIN);
        result[14] = E::from(self.public_inputs.vote_commitment)
            - prototype_hash(current[1], current[7], COMMITMENT_DOMAIN);
    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        let last_step = self.trace_length - 1;
        vec![
            Assertion::single(0, 0, BaseElement::new(CLOCK_START)),
            Assertion::single(0, last_step, BaseElement::new(last_step as u128)),
            Assertion::single(2, 0, BaseElement::ONE),
            Assertion::single(2, last_step, BaseElement::ONE),
            Assertion::single(3, 0, BaseElement::ZERO),
            Assertion::single(3, last_step, BaseElement::ZERO),
            Assertion::single(4, 0, BaseElement::ONE),
            Assertion::single(4, last_step, BaseElement::ONE),
            Assertion::single(5, 0, self.public_inputs.event_id_scalar),
            Assertion::single(5, last_step, self.public_inputs.event_id_scalar),
        ]
    }
}

struct ReferendumProver {
    options: ProofOptions,
}

impl ReferendumProver {
    fn new(options: ProofOptions) -> Self {
        Self { options }
    }
}

impl Prover for ReferendumProver {
    type BaseField = BaseElement;
    type Air = ReferendumAir;
    type Trace = TraceTable<Self::BaseField>;
    type HashFn = HashFn;
    type VC = VC;
    type RandomCoin = RandomCoin;
    type TraceLde<E: FieldElement<BaseField = Self::BaseField>> = TraceLde<E>;
    type ConstraintEvaluator<'a, E: FieldElement<BaseField = Self::BaseField>> =
        ConstraintEvaluator<'a, E>;
    type ConstraintCommitment<E: FieldElement<BaseField = Self::BaseField>> =
        ConstraintCommitment<E>;

    fn get_pub_inputs(&self, trace: &Self::Trace) -> PublicInputs {
        let event_id_scalar = trace.get(5, 0);
        let nullifier = prototype_hash_element(trace.get(6, 0), trace.get(5, 0), NULLIFIER_DOMAIN);
        let vote_commitment =
            prototype_hash_element(trace.get(1, 0), trace.get(7, 0), COMMITMENT_DOMAIN);
        PublicInputs {
            event_id_scalar,
            nullifier,
            vote_commitment,
        }
    }

    fn options(&self) -> &ProofOptions {
        &self.options
    }

    fn new_trace_lde<E: FieldElement<BaseField = Self::BaseField>>(
        &self,
        trace_info: &TraceInfo,
        main_trace: &ColMatrix<Self::BaseField>,
        domain: &StarkDomain<Self::BaseField>,
        partition_options: PartitionOptions,
    ) -> (Self::TraceLde<E>, TracePolyTable<E>) {
        DefaultTraceLde::new(trace_info, main_trace, domain, partition_options)
    }

    fn new_evaluator<'a, E: FieldElement<BaseField = Self::BaseField>>(
        &self,
        air: &'a Self::Air,
        aux_rand_elements: Option<AuxRandElements<E>>,
        composition_coefficients: ConstraintCompositionCoefficients<E>,
    ) -> Self::ConstraintEvaluator<'a, E> {
        DefaultConstraintEvaluator::new(air, aux_rand_elements, composition_coefficients)
    }

    fn build_constraint_commitment<E: FieldElement<BaseField = Self::BaseField>>(
        &self,
        composition_poly_trace: CompositionPolyTrace<E>,
        num_constraint_composition_columns: usize,
        domain: &StarkDomain<Self::BaseField>,
        partition_options: PartitionOptions,
    ) -> (Self::ConstraintCommitment<E>, CompositionPoly<E>) {
        DefaultConstraintCommitment::new(
            composition_poly_trace,
            num_constraint_composition_columns,
            domain,
            partition_options,
        )
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        return Err(
            "usage: cargo run --release -- <prove|verify> <input_json> <proof_path>".to_string(),
        );
    }

    let command = &args[1];
    let input_path = PathBuf::from(&args[2]);
    let proof_path = PathBuf::from(&args[3]);

    match command.as_str() {
        "prove" => {
            let witness = read_witness(&input_path)?;
            let public_values = public_values_from_witness(witness)?;
            let public_inputs = to_public_inputs(public_values);
            prove(witness, public_values, public_inputs, &proof_path)
        }
        "verify" => {
            let public_values = read_public_inputs(&input_path)?;
            let public_inputs = to_public_inputs(public_values);
            verify_proof(public_inputs, &proof_path)
        }
        _ => Err(format!("unsupported command: {command}")),
    }
}

fn prove(
    witness: ReferendumWitness,
    public_values: PublicInputValues,
    public_inputs: PublicInputs,
    proof_path: &Path,
) -> Result<(), String> {
    let trace = build_trace(witness)?;
    let prover = ReferendumProver::new(default_proof_options());

    let started_at = Instant::now();
    let proof = prover.prove(trace).map_err(|error| error.to_string())?;
    let elapsed = started_at.elapsed();

    let proof_bytes = proof.to_bytes();
    if let Some(parent) = proof_path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(proof_path, &proof_bytes).map_err(|error| error.to_string())?;

    println!("proof_path={}", proof_path.display());
    println!("proof_size_bytes={}", proof_bytes.len());
    println!("proof_generation_ms={:.6}", elapsed.as_secs_f64() * 1_000.0);
    println!("event_id_scalar={}", to_hex(public_values.event_id_scalar));
    println!("nullifier={}", to_hex(public_values.nullifier));
    println!("vote_commitment={}", to_hex(public_values.vote_commitment));
    println!("accepted=1");
    let _ = public_inputs;

    Ok(())
}

fn verify_proof(public_inputs: PublicInputs, proof_path: &Path) -> Result<(), String> {
    let proof_bytes = fs::read(proof_path).map_err(|error| error.to_string())?;
    let proof = Proof::from_bytes(&proof_bytes).map_err(|error| error.to_string())?;

    let started_at = Instant::now();
    verify::<ReferendumAir, HashFn, RandomCoin, MerkleTree<HashFn>>(
        proof,
        public_inputs,
        &AcceptableOptions::MinConjecturedSecurity(95),
    )
    .map_err(|error| error.to_string())?;
    let elapsed = started_at.elapsed();

    println!("verified=true");
    println!("proof_path={}", proof_path.display());
    println!(
        "proof_verification_ms={:.6}",
        elapsed.as_secs_f64() * 1_000.0
    );

    Ok(())
}

fn read_json(path: &Path) -> Result<Value, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

fn read_witness(path: &Path) -> Result<ReferendumWitness, String> {
    let json = read_json(path)?;
    let event_id = read_required_string(&json, "event_id")?;
    let event_id_scalar = encode_event_id_to_field(&event_id);

    Ok(ReferendumWitness {
        vote_value: read_required_u128(&json, "vote_value")?,
        registered_flag: read_required_u128(&json, "registered_flag")?,
        already_voted_flag: read_required_u128(&json, "already_voted_flag")?,
        event_id_scalar,
        voter_secret: read_required_u128(&json, "voter_secret")?,
        ballot_salt: read_required_u128(&json, "ballot_salt")?,
    })
}

fn read_public_inputs(path: &Path) -> Result<PublicInputValues, String> {
    let json = read_json(path)?;
    let event_id = read_required_string(&json, "event_id")?;
    let derived_event_id_scalar = encode_event_id_to_field(&event_id);

    if let Some(candidate_scalar) = read_optional_u128(&json, "event_id_scalar")? {
        if candidate_scalar != derived_event_id_scalar {
            return Err("event_id_scalar does not match the supplied event_id".to_string());
        }
    }

    Ok(PublicInputValues {
        event_id_scalar: derived_event_id_scalar,
        nullifier: read_required_u128(&json, "nullifier")?,
        vote_commitment: read_required_u128(&json, "vote_commitment")?,
    })
}

fn public_values_from_witness(witness: ReferendumWitness) -> Result<PublicInputValues, String> {
    compute_accepted(witness)?;
    Ok(PublicInputValues {
        event_id_scalar: witness.event_id_scalar,
        nullifier: prototype_hash_value(witness.voter_secret, witness.event_id_scalar, NULLIFIER_DOMAIN),
        vote_commitment: prototype_hash_value(witness.vote_value, witness.ballot_salt, COMMITMENT_DOMAIN),
    })
}

fn to_public_inputs(values: PublicInputValues) -> PublicInputs {
    PublicInputs {
        event_id_scalar: BaseElement::new(values.event_id_scalar),
        nullifier: BaseElement::new(values.nullifier),
        vote_commitment: BaseElement::new(values.vote_commitment),
    }
}

fn compute_accepted(witness: ReferendumWitness) -> Result<u128, String> {
    if witness.vote_value > 1 {
        return Err("vote_value must be binary".to_string());
    }
    if witness.registered_flag != 1 {
        return Err("registered_flag must be 1".to_string());
    }
    if witness.already_voted_flag != 0 {
        return Err("already_voted_flag must be 0".to_string());
    }

    let accepted = witness.registered_flag * (1 - witness.already_voted_flag);
    if accepted != 1 {
        return Err("accepted must be 1".to_string());
    }
    Ok(accepted)
}

fn build_trace(witness: ReferendumWitness) -> Result<TraceTable<BaseElement>, String> {
    let accepted = compute_accepted(witness)?;
    let mut clock_column = Vec::with_capacity(TRACE_LENGTH);
    for step in 0..TRACE_LENGTH {
        clock_column.push(BaseElement::new(step as u128));
    }

    Ok(TraceTable::init(vec![
        clock_column,
        vec![BaseElement::new(witness.vote_value); TRACE_LENGTH],
        vec![BaseElement::new(witness.registered_flag); TRACE_LENGTH],
        vec![BaseElement::new(witness.already_voted_flag); TRACE_LENGTH],
        vec![BaseElement::new(accepted); TRACE_LENGTH],
        vec![BaseElement::new(witness.event_id_scalar); TRACE_LENGTH],
        vec![BaseElement::new(witness.voter_secret); TRACE_LENGTH],
        vec![BaseElement::new(witness.ballot_salt); TRACE_LENGTH],
    ]))
}

fn default_proof_options() -> ProofOptions {
    ProofOptions::new(
        32,
        8,
        0,
        FieldExtension::None,
        8,
        31,
        BatchingMethod::Linear,
        BatchingMethod::Linear,
    )
}

fn read_required_string(json: &Value, key: &str) -> Result<String, String> {
    let value = json
        .get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| format!("{key} is required"))?;
    Ok(value.to_string())
}

fn read_required_u128(json: &Value, key: &str) -> Result<u128, String> {
    read_optional_u128(json, key)?.ok_or_else(|| format!("{key} is required"))
}

fn read_optional_u128(json: &Value, key: &str) -> Result<Option<u128>, String> {
    let Some(value) = json.get(key) else {
        return Ok(None);
    };
    match value {
        Value::Number(number) => number
            .to_string()
            .parse::<u128>()
            .map(Some)
            .map_err(|_| format!("{key} must be a non-negative integer")),
        Value::String(text) => parse_u128_from_str(text)
            .map(Some)
            .map_err(|_| format!("{key} must be a valid decimal or hexadecimal integer")),
        _ => Err(format!("{key} must be a valid integer")),
    }
}

fn parse_u128_from_str(value: &str) -> Result<u128, std::num::ParseIntError> {
    let trimmed = value.trim();
    if let Some(hex) = trimmed.strip_prefix("0x").or_else(|| trimmed.strip_prefix("0X")) {
        u128::from_str_radix(hex, 16)
    } else {
        trimmed.parse::<u128>()
    }
}

fn encode_event_id_to_field(event_id: &str) -> u128 {
    let mut acc = BaseElement::ZERO;
    let base = BaseElement::new(257);
    for byte in event_id.as_bytes() {
        acc = acc * base + BaseElement::new((*byte as u128) + 1);
    }
    acc.as_int()
}

fn prototype_hash_value(left: u128, right: u128, domain: u128) -> u128 {
    prototype_hash_element(
        BaseElement::new(left % FIELD_MODULUS),
        BaseElement::new(right % FIELD_MODULUS),
        domain,
    )
    .as_int()
}

fn prototype_hash_element(left: BaseElement, right: BaseElement, domain: u128) -> BaseElement {
    let domain_element = BaseElement::new(domain);
    let one = BaseElement::ONE;
    let two = BaseElement::new(2);

    let x = left + domain_element;
    let y = right + domain_element + one;
    let z = left + right + domain_element + two;

    x.exp(3u32.into())
        + BaseElement::new(5) * y.exp(3u32.into())
        + BaseElement::new(7) * z.exp(3u32.into())
        + BaseElement::new(11) * x * y
        + BaseElement::new(13) * y * z
        + BaseElement::new(17) * x * z
        + BaseElement::new(19) * domain_element
}

fn prototype_hash<E: FieldElement<BaseField = BaseElement> + From<BaseElement>>(
    left: E,
    right: E,
    domain: u128,
) -> E {
    let domain_element = E::from(BaseElement::new(domain));
    let one = E::ONE;
    let two = E::from(BaseElement::new(2));

    let x = left + domain_element;
    let y = right + domain_element + one;
    let z = left + right + domain_element + two;

    x.exp(3u32.into())
        + E::from(BaseElement::new(5)) * y.exp(3u32.into())
        + E::from(BaseElement::new(7)) * z.exp(3u32.into())
        + E::from(BaseElement::new(11)) * x * y
        + E::from(BaseElement::new(13)) * y * z
        + E::from(BaseElement::new(17)) * x * z
        + E::from(BaseElement::new(19)) * domain_element
}

fn to_hex(value: u128) -> String {
    format!("0x{value:032x}")
}
