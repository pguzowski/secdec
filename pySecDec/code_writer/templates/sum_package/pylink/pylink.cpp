#include "%(name)s.hpp"

#include <vector>
#include <memory> // std::shared_ptr, std::make_shared
#include <string>
#include <sstream>

#include <secdecutil/uncertainties.hpp> // secdecutil::UncorrelatedDeviation

#define INTEGRAL_NAME %(name)s

#define integral_need_complex %(need_complex)i 

#include <secdecutil/pylink.hpp> // The python-C binding is general and therefore contained in the util
#include <secdecutil/pylink_amplitude.hpp>

// delegate some template instatiations to separate translation units
#ifdef SECDEC_WITH_CUDA
    #define EXTERN_KOROBOV_QMC_SEPARATE(KOROBOVDEGREE1,KOROBOVDEGREE2) \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               secdecutil::integrators::void_template \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               ::integrators::fitfunctions::None::type \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               ::integrators::fitfunctions::PolySingular::type \
                                                          >;
    #define EXTERN_SIDI_QMC_SEPARATE(SIDIDEGREE) \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               secdecutil::integrators::void_template \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               ::integrators::fitfunctions::None::type \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::cuda_integrand_t, \
                                                               ::integrators::fitfunctions::PolySingular::type \
                                                          >;
    #if %(name)s_number_of_sectors != 1
        #define EXTERN_KOROBOV_QMC(KOROBOVDEGREE1,KOROBOVDEGREE2) \
            EXTERN_KOROBOV_QMC_SEPARATE(KOROBOVDEGREE1,KOROBOVDEGREE2) \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   secdecutil::integrators::void_template \
                                                              >; \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   ::integrators::fitfunctions::None::type \
                                                              >; \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   ::integrators::fitfunctions::PolySingular::type \
                                                              >;
        #define EXTERN_SIDI_QMC(SIDIDEGREE) \
            EXTERN_SIDI_QMC_SEPARATE(SIDIDEGREE) \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   secdecutil::integrators::void_template \
                                                              >; \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   ::integrators::fitfunctions::None::type \
                                                              >; \
            extern template class secdecutil::integrators::Qmc< \
                                                                   INTEGRAL_NAME::integrand_return_t, \
                                                                   INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                   ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                   INTEGRAL_NAME::cuda_together_integrand_t, \
                                                                   ::integrators::fitfunctions::PolySingular::type \
                                                              >;
    #else
        #define EXTERN_KOROBOV_QMC(KOROBOVDEGREE1,KOROBOVDEGREE2) EXTERN_KOROBOV_QMC_SEPARATE(KOROBOVDEGREE1,KOROBOVDEGREE2)
        #define EXTERN_SIDI_QMC(SIDIDEGREE) EXTERN_SIDI_QMC_SEPARATE(SIDIDEGREE)
    #endif
#else
    #define EXTERN_KOROBOV_QMC(KOROBOVDEGREE1,KOROBOVDEGREE2) \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               secdecutil::integrators::void_template \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               ::integrators::fitfunctions::None::type \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Korobov<KOROBOVDEGREE1,KOROBOVDEGREE2>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               ::integrators::fitfunctions::PolySingular::type \
                                                          >;
    #define EXTERN_SIDI_QMC(SIDIDEGREE) \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               secdecutil::integrators::void_template \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               ::integrators::fitfunctions::None::type \
                                                          >; \
        extern template class secdecutil::integrators::Qmc< \
                                                               INTEGRAL_NAME::integrand_return_t, \
                                                               INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                               ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                               INTEGRAL_NAME::integrand_t, \
                                                               ::integrators::fitfunctions::PolySingular::type \
                                                          >;
#endif

%(pylink_qmc_externs)s

#undef EXTERN_KOROBOV_QMC
#undef EXTERN_SIDI_QMC
#undef EXTERN_KOROBOV_QMC_SEPARATE
#undef EXTERN_SIDI_QMC_SEPARATE
#undef %(name)s_number_of_sectors

// common qmc args and defaults
#define COMMON_ALLOCATE_QMC_ARGS \
    double epsrel, \
    double epsabs, \
    unsigned long long int maxeval, \
    int errormode, \
    unsigned long long int evaluateminn, \
    unsigned long long int minn, \
    unsigned long long int minm, \
    unsigned long long int maxnperpackage, \
    unsigned long long int maxmperpackage, \
    unsigned long long int cputhreads, \
    unsigned long long int cudablocks, \
    unsigned long long int cudathreadsperblock, \
    unsigned long long int verbosity, \
    long long int seed, \
    int transform_id, \
    int fitfunction_id, \
    int generatingvectors_id
#define SET_COMMON_QMC_ARGS \
    /* If an argument is set to 0 then use the default of the Qmc library */ \
    if ( epsrel != 0 ) \
        integrator->epsrel = epsrel; \
    if ( epsabs != 0 ) \
        integrator->epsabs = epsabs; \
    if ( maxeval != 0 ) \
        integrator->maxeval = maxeval; \
    if ( errormode != 0 ) \
        integrator->errormode = static_cast<::integrators::ErrorMode>(errormode); \
    if ( evaluateminn != 0 ) \
        integrator->evaluateminn = evaluateminn; \
    if ( minn != 0 ) \
        integrator->minn = minn; \
    if ( minm != 0 ) \
        integrator->minm = minm; \
    if ( maxnperpackage != 0 ) \
        integrator->maxnperpackage = maxnperpackage; \
    if ( maxmperpackage != 0 ) \
        integrator->maxmperpackage = maxmperpackage; \
    if ( cputhreads != 0 ) \
        integrator->cputhreads = cputhreads; \
    if ( cudablocks != 0 ) \
        integrator->cudablocks = cudablocks; \
    if ( cudathreadsperblock != 0 ) \
        integrator->cudathreadsperblock = cudathreadsperblock; \
    if ( verbosity != 0 ) \
        integrator->verbosity = verbosity; \
    if ( seed != 0 ) \
        integrator->randomgenerator.seed(seed); \
    if ( generatingvectors_id == cbcpt_dn1_100 ) \
        integrator->generatingvectors = ::integrators::generatingvectors::cbcpt_dn1_100(); \
    if ( generatingvectors_id == cbcpt_dn2_6 ) \
        integrator->generatingvectors = ::integrators::generatingvectors::cbcpt_dn2_6(); \
    if ( generatingvectors_id == cbcpt_cfftw1_6 ) \
        integrator->generatingvectors = ::integrators::generatingvectors::cbcpt_cfftw1_6(); \
    if ( generatingvectors_id == cbcpt_cfftw2_10 ) \
        integrator->generatingvectors = ::integrators::generatingvectors::cbcpt_cfftw2_10(); \
    integrator->logger = std::cerr;
#define SET_QMC_ARGS_WITH_DEVICES_AND_RETURN \
        SET_COMMON_QMC_ARGS \
        if (number_of_devices > 0) \
        { \
            integrator->devices.clear(); \
            for (int i = 0; i < number_of_devices; ++i) \
                integrator->devices.insert( devices[i] ); \
        } \
        return integrator;
#define SET_QMC_ARGS_AND_RETURN \
        SET_COMMON_QMC_ARGS \
        return integrator;

// all known qmc options
enum qmc_transform_t : int
{
    no_transform = -1,

    baker = -2,

    korobov1x1 = 1, korobov1x2 = 2, korobov1x3 = 3, korobov1x4 = 4, korobov1x5 = 5, korobov1x6 = 6,
    korobov2x1 = 7, korobov2x2 = 8, korobov2x3 = 9, korobov2x4 = 10, korobov2x5 = 11, korobov2x6 = 12,
    korobov3x1 = 13, korobov3x2 = 14, korobov3x3 = 15, korobov3x4 = 16, korobov3x5 = 17, korobov3x6 = 18,
    korobov4x1 = 19, korobov4x2 = 20, korobov4x3 = 21, korobov4x4 = 22, korobov4x5 = 23, korobov4x6 = 24,
    korobov5x1 = 25, korobov5x2 = 26, korobov5x3 = 27, korobov5x4 = 28, korobov5x5 = 29, korobov5x6 = 30,
    korobov6x1 = 31, korobov6x2 = 32, korobov6x3 = 33, korobov6x4 = 34, korobov6x5 = 35, korobov6x6 = 36,

    sidi1 = -11,
    sidi2 = -12,
    sidi3 = -13,
    sidi4 = -14,
    sidi5 = -15,
    sidi6 = -16
};
enum qmc_fitfunction_t : int
{
    default_fitfunction = 0,

    no_fit = -1,
    polysingular = 1
};
enum qmc_generatingvectors_t : int
{
    default_generatingvectors = 0,

    cbcpt_dn1_100 = 1,
    cbcpt_dn2_6 = 2,
    cbcpt_cfftw1_6 = 3,
    cbcpt_cfftw2_10 = 4
};

#define CASE_KOROBOV_QMC(KOROBOVDEGREE1,KOROBOVDEGREE2) \
    } else if (transform_id == korobov##KOROBOVDEGREE1##x##KOROBOVDEGREE2) { \
        if (fitfunction_id == default_fitfunction) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Korobov<KOROBOVDEGREE1, KOROBOVDEGREE2>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else if (fitfunction_id == no_fit) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Korobov<KOROBOVDEGREE1, KOROBOVDEGREE2>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME, \
                                                                  ::integrators::fitfunctions::None::type \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else if (fitfunction_id == polysingular) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Korobov<KOROBOVDEGREE1, KOROBOVDEGREE2>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME, \
                                                                  ::integrators::fitfunctions::PolySingular::type \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else { \
            throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ")."); \
        }

#define CASE_SIDI_QMC(SIDIDEGREE) \
    } else if (transform_id == sidi##SIDIDEGREE) { \
        if (fitfunction_id == default_fitfunction) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else if (fitfunction_id == no_fit) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME, \
                                                                  ::integrators::fitfunctions::None::type \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else if (fitfunction_id == polysingular) { \
            auto integrator = new secdecutil::integrators::Qmc< \
                                                                  INTEGRAL_NAME::integrand_return_t, \
                                                                  INTEGRAL_NAME::maximal_number_of_integration_variables, \
                                                                  ::integrators::transforms::Sidi<SIDIDEGREE>::type, \
                                                                  INTEGRAL_NAME::QMC_INTEGRAND_TYPENAME, \
                                                                  ::integrators::fitfunctions::PolySingular::type \
                                                              >; \
            QMC_RETURN_STATEMENT \
        } else { \
            throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ")."); \
        }

// qmc allocate functions implementation
#ifdef SECDEC_WITH_CUDA
    secdecutil::Integrator<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::real_t,INTEGRAL_NAME::cuda_together_integrand_t> *
    allocate_cuda_integrators_Qmc_together(
                                               COMMON_ALLOCATE_QMC_ARGS,
                                               unsigned long long int number_of_devices,
                                               int devices[]
                                          )
    {
        if (transform_id == no_transform) {

            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_together_integrand_t>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_together_integrand_t,::integrators::fitfunctions::None::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_together_integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }

        } else if (transform_id == baker) {
            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::cuda_together_integrand_t>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::cuda_together_integrand_t,::integrators::fitfunctions::None::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::cuda_together_integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }
            
        #define QMC_INTEGRAND_TYPENAME cuda_together_integrand_t
        #define QMC_RETURN_STATEMENT SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
        %(pylink_qmc_cases)s
        #undef QMC_INTEGRAND_TYPENAME
            
        } else {
            throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"transform_id\" (" + std::to_string(transform_id) + "). The transform you requested in the call to IntegralLibrary (transform='...') must match a transform requested in the generate script (pylink_qmc_transforms=['...']). You may wish to regenerate the library with pylink_qmc_transforms set.");
        }
    }
    secdecutil::Integrator<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::real_t,INTEGRAL_NAME::cuda_integrand_t> *
    allocate_cuda_integrators_Qmc_separate(
                                               COMMON_ALLOCATE_QMC_ARGS,
                                               unsigned long long int number_of_devices,
                                               int devices[]
                                          )
    {
        if (transform_id == no_transform) {

            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_integrand_t>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_integrand_t,::integrators::fitfunctions::None::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::cuda_integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }

        } else if (transform_id == baker) {
            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,cuda_integrand_t>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::cuda_integrand_t,::integrators::fitfunctions::None::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::cuda_integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }

        #define QMC_INTEGRAND_TYPENAME cuda_integrand_t
        #define QMC_RETURN_STATEMENT SET_QMC_ARGS_WITH_DEVICES_AND_RETURN
        %(pylink_qmc_cases)s
        #undef QMC_INTEGRAND_TYPENAME

        } else {
            throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"transform_id\" (" + std::to_string(transform_id) + "). The transform you requested in the call to IntegralLibrary (transform='...') must match a transform requested in the generate script (pylink_qmc_transforms=['...']). You may wish to regenerate the library with pylink_qmc_transforms set.");
        }
    }
#else
    secdecutil::Integrator<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::real_t> *
    allocate_integrators_Qmc(COMMON_ALLOCATE_QMC_ARGS)
    {
        if (transform_id == no_transform) {

            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::integrand_t>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::integrand_t,::integrators::fitfunctions::None::type>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::None::type,INTEGRAL_NAME::integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }

        } else if (transform_id == baker) {
            if (fitfunction_id == default_fitfunction) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::integrand_t>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else if (fitfunction_id == no_fit) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::integrand_t,::integrators::fitfunctions::None::type>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else if (fitfunction_id == polysingular) {
                auto integrator = new secdecutil::integrators::Qmc<INTEGRAL_NAME::integrand_return_t,INTEGRAL_NAME::maximal_number_of_integration_variables,::integrators::transforms::Baker::type,INTEGRAL_NAME::integrand_t,::integrators::fitfunctions::PolySingular::type>;
                SET_COMMON_QMC_ARGS
                return integrator;
            } else {
                throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"fitfunction_id\" (" + std::to_string(fitfunction_id) + ").");
            }
            
        #define QMC_INTEGRAND_TYPENAME integrand_t
        #define QMC_RETURN_STATEMENT SET_QMC_ARGS_AND_RETURN
        %(pylink_qmc_cases)s
        #undef QMC_INTEGRAND_TYPENAME

        } else {
            throw std::invalid_argument("Trying to allocate \"secdecutil::Qmc\" with unregistered \"transform_id\" (" + std::to_string(transform_id) + "). The transform you requested in the call to IntegralLibrary (transform='...') must match a transform requested in the generate script (pylink_qmc_transforms=['...']). You may wish to regenerate the library with pylink_qmc_transforms set.");
        }
    }
#endif
#undef COMMON_ALLOCATE_QMC_ARGS
#undef SET_COMMON_QMC_ARGS
#undef SET_QMC_ARGS_WITH_DEVICES_AND_RETURN

#undef integral_need_complex
