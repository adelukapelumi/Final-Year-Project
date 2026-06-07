use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use serde::Deserialize;
use winterfell::crypto::hashers::Blake3_256;
use winterfell::crypto::{DefaultRandomCoin, MerkleTree};
use winterfell::math::{fields::f128::BaseElement, FieldElement, ToElements};
use winterfell::{
    verify, AcceptableOptions, Air, AirContext, Assertion, AuxRandElements, BatchingMethod,
    CompositionPoly, CompositionPolyTrace, ConstraintCompositionCoefficients,
    DefaultConstraintCommitment, DefaultConstraintEvaluator, DefaultTraceLde,
    Deserializable, EvaluationFrame, FieldExtension, PartitionOptions, Proof, ProofOptions,
    Prover, Serializable, StarkDomain, TraceInfo, TracePolyTable, TraceTable,
    TransitionConstraintDegree,
};

const TRACE_LENGTH: usize = 8;
const ACCEPTED_VALUE: u64 = 1;

type HashFn = Blake3_256<BaseElement>;
type VC = MerkleTree<HashFn>;
type RandomCoin = DefaultRandomCoin<HashFn>;
type TraceLde<E> = DefaultTraceLde<E, HashFn, VC>;
type ConstraintEvaluator<'a, E> = DefaultConstraintEvaluator<'a, ReferendumAir, E>;
type ConstraintCommitment<E> = DefaultConstraintCommitment<E, HashFn, VC>;

#[derive(Debug, Clone, Copy)]
struct ReferendumInput {
    vote_value: u64,
    registered_flag: u64,
    already_voted_flag: u64,
}

#[derive(Debug, Clone, Copy)]
struct PublicInputs {
    vote_value: BaseElement,
    registered_flag: BaseElement,
    already_voted_flag: BaseElement,
    accepted: BaseElement,
}

impl ToElements<BaseElement> for PublicInputs {
    fn to_elements(&self) -> Vec<BaseElement> {
        vec![
            self.vote_value,
            self.registered_flag,
            self.already_voted_flag,
            self.accepted,
        ]
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
        assert_eq!(4, trace_info.width());
        let degrees = vec![
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(1),
            TransitionConstraintDegree::new(2),
            TransitionConstraintDegree::new(1),
        ];
        let trace_length = trace_info.length();
        let num_assertions = 8;

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

        result[0] = next[0] - current[0];
        result[1] = next[1] - current[1];
        result[2] = next[2] - current[2];
        result[3] = next[3] - current[3];
        result[4] = current[0] * (current[0] - one);
        result[5] = current[1] - one;
        result[6] = current[2];
        result[7] = current[3] - (current[1] * (one - current[2]));
        result[8] = current[3] - one;
    }

    fn get_assertions(&self) -> Vec<Assertion<Self::BaseField>> {
        let last_step = self.trace_length - 1;
        vec![
            Assertion::single(0, 0, self.public_inputs.vote_value),
            Assertion::single(1, 0, self.public_inputs.registered_flag),
            Assertion::single(2, 0, self.public_inputs.already_voted_flag),
            Assertion::single(3, 0, self.public_inputs.accepted),
            Assertion::single(0, last_step, self.public_inputs.vote_value),
            Assertion::single(1, last_step, self.public_inputs.registered_flag),
            Assertion::single(2, last_step, self.public_inputs.already_voted_flag),
            Assertion::single(3, last_step, self.public_inputs.accepted),
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
        PublicInputs {
            vote_value: trace.get(0, 0),
            registered_flag: trace.get(1, 0),
            already_voted_flag: trace.get(2, 0),
            accepted: trace.get(3, 0),
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

use winterfell::matrix::ColMatrix;

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
    let input = read_input(&input_path)?;
    let accepted = compute_accepted(input)?;
    let public_inputs = build_public_inputs(input, accepted);

    match command.as_str() {
        "prove" => prove(input, public_inputs, &proof_path),
        "verify" => verify_proof(public_inputs, &proof_path),
        _ => Err(format!("unsupported command: {command}")),
    }
}

fn prove(input: ReferendumInput, public_inputs: PublicInputs, proof_path: &Path) -> Result<(), String> {
    let trace = build_trace(input)?;
    let prover = ReferendumProver::new(default_proof_options());

    let started_at = Instant::now();
    let proof = prover.prove(trace).map_err(|error| error.to_string())?;
    let elapsed = started_at.elapsed();

    let proof_bytes = proof.to_bytes();
    if let Some(parent) = proof_path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(proof_path, &proof_bytes).map_err(|error| error.to_string())?;

    println!("accepted={}", ACCEPTED_VALUE);
    println!("proof_path={}", proof_path.display());
    println!("proof_size_bytes={}", proof_bytes.len());
    println!("proof_generation_ms={}", elapsed.as_millis());

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
    println!("proof_verification_ms={}", elapsed.as_millis());

    Ok(())
}

fn read_input(path: &Path) -> Result<ReferendumInput, String> {
    #[derive(Deserialize)]
    struct RawInput {
        vote_value: u64,
        registered_flag: u64,
        already_voted_flag: u64,
    }

    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let input: RawInput = serde_json::from_str(&raw).map_err(|error| error.to_string())?;

    Ok(ReferendumInput {
        vote_value: input.vote_value,
        registered_flag: input.registered_flag,
        already_voted_flag: input.already_voted_flag,
    })
}

fn compute_accepted(input: ReferendumInput) -> Result<u64, String> {
    if input.vote_value > 1 {
        return Err("vote_value must be binary".to_string());
    }
    if input.registered_flag != 1 {
        return Err("registered_flag must be 1".to_string());
    }
    if input.already_voted_flag != 0 {
        return Err("already_voted_flag must be 0".to_string());
    }

    let accepted = input.registered_flag * (ACCEPTED_VALUE - input.already_voted_flag);
    if accepted != ACCEPTED_VALUE {
        return Err("accepted must be 1".to_string());
    }

    Ok(accepted)
}

fn build_public_inputs(input: ReferendumInput, accepted: u64) -> PublicInputs {
    PublicInputs {
        vote_value: BaseElement::new(input.vote_value.into()),
        registered_flag: BaseElement::new(input.registered_flag.into()),
        already_voted_flag: BaseElement::new(input.already_voted_flag.into()),
        accepted: BaseElement::new(accepted.into()),
    }
}

fn build_trace(input: ReferendumInput) -> Result<TraceTable<BaseElement>, String> {
    let accepted = compute_accepted(input)?;
    let trace = TraceTable::init(vec![
        vec![BaseElement::new(input.vote_value.into()); TRACE_LENGTH],
        vec![BaseElement::new(input.registered_flag.into()); TRACE_LENGTH],
        vec![BaseElement::new(input.already_voted_flag.into()); TRACE_LENGTH],
        vec![BaseElement::new(accepted.into()); TRACE_LENGTH],
    ]);

    Ok(trace)
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
